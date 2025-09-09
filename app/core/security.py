"""
Security utilities and middleware for the FRA Decision Support System
"""

import hashlib
import secrets
import hmac
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import re
import logging
from functools import wraps

from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt
import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_db
from app.database.models.user_models import User, AuditLog, UserRole

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=30)
PASSWORD_MIN_LENGTH = 8
SESSION_TIMEOUT = timedelta(hours=8)

class SecurityError(Exception):
    """Base security exception"""
    pass

class AuthenticationError(SecurityError):
    """Authentication failed"""
    pass

class AuthorizationError(SecurityError):
    """Authorization failed"""
    pass

class DataValidationError(SecurityError):
    """Data validation failed"""
    pass

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)

def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str, expected_token: str) -> bool:
    """Validate CSRF token using constant-time comparison"""
    return hmac.compare_digest(token, expected_token)

class PasswordValidator:
    """Password strength validator"""
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        errors = []
        score = 0
        
        # Length check
        if len(password) < PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
        else:
            score += min(len(password) - PASSWORD_MIN_LENGTH, 5)
        
        # Character type checks
        if re.search(r'[a-z]', password):
            score += 1
        else:
            errors.append("Password must contain at least one lowercase letter")
            
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            errors.append("Password must contain at least one uppercase letter")
            
        if re.search(r'\d', password):
            score += 1
        else:
            errors.append("Password must contain at least one digit")
            
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 2
        else:
            errors.append("Password must contain at least one special character")
        
        # Common password check
        common_passwords = [
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon"
        ]
        if password.lower() in common_passwords:
            errors.append("Password is too common")
            score = 0
        
        # Calculate strength
        if score >= 8:
            strength = "strong"
        elif score >= 5:
            strength = "medium"
        else:
            strength = "weak"
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "score": score,
            "strength": strength
        }

class InputSanitizer:
    """Input sanitization and validation"""
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 255) -> str:
        """Sanitize string input"""
        if not input_str:
            return ""
        
        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f]', '', input_str)
        
        # Truncate to max length
        sanitized = sanitized[:max_length]
        
        # Strip whitespace
        sanitized = sanitized.strip()
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Indian phone number pattern
        pattern = r'^[+]?[91]?[6-9]\d{9}$'
        return bool(re.match(pattern, phone.replace(' ', '').replace('-', '')))
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal"""
        # Remove path separators and dangerous characters
        sanitized = re.sub(r'[/\\:*?"<>|]', '_', filename)
        
        # Remove leading dots and spaces
        sanitized = sanitized.lstrip('. ')
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "unnamed_file"
        
        return sanitized
    
    @staticmethod
    def validate_coordinates(lat: float, lng: float) -> bool:
        """Validate geographic coordinates"""
        return -90 <= lat <= 90 and -180 <= lng <= 180

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis
        self.cleanup_interval = timedelta(minutes=15)
        self.last_cleanup = datetime.utcnow()
    
    def is_allowed(self, identifier: str, limit: int, window: timedelta) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.utcnow()
        
        # Cleanup old entries
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = now
        
        # Get request history for identifier
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        request_times = self.requests[identifier]
        
        # Remove requests outside the window
        cutoff = now - window
        request_times = [t for t in request_times if t > cutoff]
        self.requests[identifier] = request_times
        
        # Check if under limit
        if len(request_times) >= limit:
            return False
        
        # Add current request
        request_times.append(now)
        return True
    
    def _cleanup_old_entries(self):
        """Clean up old rate limit entries"""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                t for t in self.requests[identifier] if t > cutoff
            ]
            if not self.requests[identifier]:
                del self.requests[identifier]

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(limit: int, window_minutes: int = 15):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                identifier = request.client.host
                window = timedelta(minutes=window_minutes)
                
                if not rate_limiter.is_allowed(identifier, limit, window):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded: {limit} requests per {window_minutes} minutes"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class PermissionChecker:
    """Permission checking utilities"""
    
    @staticmethod
    def check_resource_access(user: User, resource_type: str, resource_data: Dict[str, Any]) -> bool:
        """Check if user has access to specific resource"""
        
        # Admin has access to everything
        if user.role == UserRole.ADMIN:
            return True
        
        # Government officials have state-level access
        if user.role == UserRole.GOVERNMENT_OFFICIAL:
            if user.state and resource_data.get('state') == user.state:
                return True
        
        # Field workers have district-level access
        if user.role == UserRole.FIELD_WORKER:
            if (user.state and user.district and 
                resource_data.get('state') == user.state and
                resource_data.get('district') == user.district):
                return True
        
        # Tribal community members have village-level access
        if user.role == UserRole.TRIBAL_COMMUNITY:
            if (user.state and user.district and user.village and
                resource_data.get('state') == user.state and
                resource_data.get('district') == user.district and
                resource_data.get('village') == user.village):
                return True
        
        return False
    
    @staticmethod
    def get_data_scope(user: User) -> Dict[str, Any]:
        """Get data access scope for user"""
        if user.role == UserRole.ADMIN:
            return {"scope": "national"}
        
        elif user.role == UserRole.GOVERNMENT_OFFICIAL:
            return {
                "scope": "state",
                "state": user.state
            }
        
        elif user.role == UserRole.FIELD_WORKER:
            return {
                "scope": "district",
                "state": user.state,
                "district": user.district
            }
        
        elif user.role == UserRole.TRIBAL_COMMUNITY:
            return {
                "scope": "village",
                "state": user.state,
                "district": user.district,
                "village": user.village
            }
        
        return {"scope": "none"}

async def create_audit_log(
    db: AsyncSession,
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    request: Request,
    success: bool,
    error_message: Optional[str] = None,
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
    processing_time_ms: Optional[int] = None
):
    """Create audit log entry"""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            method=request.method,
            endpoint=str(request.url),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_data=request_data,
            response_data=response_data,
            status_code=200 if success else 500,
            success=success,
            error_message=error_message,
            processing_time_ms=processing_time_ms
        )
        
        db.add(audit_log)
        await db.commit()
        
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        # Don't let audit log failure affect the main operation

class DataEncryption:
    """Data encryption utilities"""
    
    @staticmethod
    def encrypt_sensitive_data(data: str, key: Optional[str] = None) -> str:
        """Encrypt sensitive data (placeholder implementation)"""
        # In production, use proper encryption like AES
        if not key:
            key = settings.SECRET_KEY
        
        # Simple XOR encryption for demonstration
        # Replace with proper encryption in production
        encrypted = ""
        for i, char in enumerate(data):
            key_char = key[i % len(key)]
            encrypted += chr(ord(char) ^ ord(key_char))
        
        return encrypted.encode('utf-8').hex()
    
    @staticmethod
    def decrypt_sensitive_data(encrypted_data: str, key: Optional[str] = None) -> str:
        """Decrypt sensitive data (placeholder implementation)"""
        if not key:
            key = settings.SECRET_KEY
        
        try:
            # Convert from hex
            data = bytes.fromhex(encrypted_data).decode('utf-8')
            
            # Simple XOR decryption
            decrypted = ""
            for i, char in enumerate(data):
                key_char = key[i % len(key)]
                decrypted += chr(ord(char) ^ ord(key_char))
            
            return decrypted
        except Exception:
            return ""

def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data for logging/display"""
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)

class SecurityHeaders:
    """Security headers middleware"""
    
    @staticmethod
    def add_security_headers(response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=()"
        )
        
        return response

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from function arguments
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break
            
            # Check in kwargs
            if not user:
                user = kwargs.get('current_user')
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permission (simplified - in production, use proper RBAC)
            role_permissions = {
                UserRole.ADMIN: ["*"],  # All permissions
                UserRole.GOVERNMENT_OFFICIAL: [
                    "read_claims", "write_claims", "verify_claims", 
                    "generate_reports", "view_analytics"
                ],
                UserRole.FIELD_WORKER: [
                    "read_assigned_claims", "update_verification", 
                    "upload_documents", "gps_marking"
                ],
                UserRole.TRIBAL_COMMUNITY: [
                    "view_own_claims", "submit_claims", 
                    "upload_documents", "check_status"
                ]
            }
            
            user_permissions = role_permissions.get(user.role, [])
            
            if "*" not in user_permissions and permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Data anonymization functions
def anonymize_personal_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Anonymize personal data for analytics"""
    sensitive_fields = [
        'name', 'email', 'phone', 'address', 'aadhar_number', 
        'voter_id', 'ration_card_number', 'bank_account'
    ]
    
    anonymized = data.copy()
    for field in sensitive_fields:
        if field in anonymized:
            if isinstance(anonymized[field], str):
                # Replace with hash
                anonymized[field] = hashlib.sha256(
                    anonymized[field].encode()
                ).hexdigest()[:16]
    
    return anonymized

def generate_data_hash(data: Any) -> str:
    """Generate hash for data integrity verification"""
    import json
    data_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(data_str.encode()).hexdigest()

# Security configuration
SECURITY_CONFIG = {
    "password_policy": {
        "min_length": PASSWORD_MIN_LENGTH,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special_chars": True,
        "max_age_days": 90,
        "history_count": 5
    },
    "session_policy": {
        "timeout_hours": 8,
        "max_concurrent_sessions": 3,
        "require_reauth_for_sensitive": True
    },
    "rate_limiting": {
        "login_attempts": {"limit": 5, "window_minutes": 15},
        "api_requests": {"limit": 1000, "window_minutes": 60},
        "file_uploads": {"limit": 10, "window_minutes": 60}
    },
    "data_retention": {
        "audit_logs_days": 2555,  # 7 years
        "session_logs_days": 90,
        "temp_files_hours": 24
    }
}