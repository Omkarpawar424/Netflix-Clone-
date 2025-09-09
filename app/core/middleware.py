"""
Middleware for security, logging, and request processing
"""

import time
import logging
import uuid
from typing import Callable
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import SecurityHeaders, rate_limiter, create_audit_log
from app.database.models.user_models import User

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for headers and basic protection"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Add request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add security headers
        response = await call_next(request)
        response = SecurityHeaders.add_security_headers(response)
        response.headers["X-Request-ID"] = request_id
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        identifier = f"{client_ip}:{hash(user_agent) % 10000}"
        
        # Check rate limit
        from datetime import timedelta
        if not rate_limiter.is_allowed(identifier, self.calls, timedelta(minutes=self.period)):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        return await call_next(request)

class AuditMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # Skip audit logging for certain endpoints
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get user ID if available
        user_id = None
        try:
            # Extract user from authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # In a real implementation, decode JWT to get user ID
                # For now, we'll skip this part
                pass
        except Exception:
            pass
        
        # Process request
        error_message = None
        success = True
        
        try:
            response = await call_next(request)
            success = response.status_code < 400
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            
            # Create audit log
            try:
                async with AsyncSessionLocal() as db:
                    await create_audit_log(
                        db=db,
                        user_id=user_id,
                        action=f"{request.method}_{request.url.path}",
                        resource_type="api_endpoint",
                        resource_id=request.url.path,
                        request=request,
                        success=success,
                        error_message=error_message,
                        processing_time_ms=processing_time
                    )
            except Exception as audit_error:
                logger.error(f"Failed to create audit log: {audit_error}")
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url} - "
            f"Client: {request.client.host if request.client else 'unknown'} - "
            f"User-Agent: {request.headers.get('user-agent', 'unknown')}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            processing_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response: {response.status_code} - "
                f"Time: {processing_time:.3f}s - "
                f"Request ID: {getattr(request.state, 'request_id', 'unknown')}"
            )
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"Error: {str(e)} - "
                f"Time: {processing_time:.3f}s - "
                f"Request ID: {getattr(request.state, 'request_id', 'unknown')}"
            )
            raise

class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with enhanced security"""
    
    def __init__(self, app, allow_origins: list = None, allow_methods: list = None, allow_headers: list = None):
        super().__init__(app)
        self.allow_origins = allow_origins or ["http://localhost:3000"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-Token"
        ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            if origin in self.allow_origins or "*" in self.allow_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
                response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        
        # Process regular requests
        response = await call_next(request)
        
        # Add CORS headers
        if origin in self.allow_origins or "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
        
        return response

class DataSanitizationMiddleware(BaseHTTPMiddleware):
    """Data sanitization middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Sanitize request headers
        self._sanitize_headers(request)
        
        # Process request
        response = await call_next(request)
        
        # Sanitize response headers (remove sensitive information)
        self._sanitize_response_headers(response)
        
        return response
    
    def _sanitize_headers(self, request: Request):
        """Sanitize request headers"""
        # Remove or mask sensitive headers
        sensitive_headers = ["x-real-ip", "x-forwarded-for", "x-original-forwarded-for"]
        
        for header in sensitive_headers:
            if header in request.headers:
                # Log for security monitoring but don't modify (readonly)
                logger.debug(f"Sensitive header detected: {header}")
    
    def _sanitize_response_headers(self, response: Response):
        """Sanitize response headers"""
        # Remove server information
        if "server" in response.headers:
            del response.headers["server"]
        
        # Remove version information
        version_headers = ["x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"]
        for header in version_headers:
            if header in response.headers:
                del response.headers[header]

class ContentValidationMiddleware(BaseHTTPMiddleware):
    """Content validation middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Validate content type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            # Check for valid content types
            valid_types = [
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
                "text/plain"
            ]
            
            if not any(content_type.startswith(vt) for vt in valid_types):
                logger.warning(f"Invalid content type: {content_type}")
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Unsupported media type"
                )
        
        # Validate content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                max_size = 100 * 1024 * 1024  # 100MB
                if length > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request entity too large"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid content length"
                )
        
        return await call_next(request)

class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Health check middleware"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Add health metrics to request state
        request.state.start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Add performance metrics to response headers
            processing_time = time.time() - request.state.start_time
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
            
            return response
            
        except Exception as e:
            # Log health issues
            processing_time = time.time() - request.state.start_time
            logger.error(
                f"Health issue detected: {str(e)} - "
                f"Processing time: {processing_time:.3f}s"
            )
            raise

class TrustedProxyMiddleware(BaseHTTPMiddleware):
    """Trusted proxy middleware for handling X-Forwarded headers"""
    
    def __init__(self, app, trusted_proxies: list = None):
        super().__init__(app)
        self.trusted_proxies = trusted_proxies or ["127.0.0.1", "::1"]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check if request is from trusted proxy
        client_ip = request.client.host if request.client else None
        
        if client_ip in self.trusted_proxies:
            # Use X-Forwarded-For header if available
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                # Take the first IP (client IP)
                real_ip = forwarded_for.split(",")[0].strip()
                # Update request client info (if possible)
                logger.debug(f"Real client IP from proxy: {real_ip}")
            
            # Use X-Forwarded-Proto for protocol
            forwarded_proto = request.headers.get("x-forwarded-proto")
            if forwarded_proto:
                logger.debug(f"Real protocol from proxy: {forwarded_proto}")
        
        return await call_next(request)

# Middleware configuration
def setup_middleware(app):
    """Setup all middleware in correct order"""
    
    # Add middleware in reverse order (last added is executed first)
    
    # Health check (outermost)
    app.add_middleware(HealthCheckMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # Content validation
    app.add_middleware(ContentValidationMiddleware)
    
    # Data sanitization
    app.add_middleware(DataSanitizationMiddleware)
    
    # CORS (before security headers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000", "*"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"]
    )
    
    # Audit logging
    app.add_middleware(AuditMiddleware)
    
    # Rate limiting
    app.add_middleware(RateLimitMiddleware, calls=1000, period=60)
    
    # Security headers (innermost, closest to app)
    app.add_middleware(SecurityMiddleware)
    
    logger.info("All middleware configured successfully")