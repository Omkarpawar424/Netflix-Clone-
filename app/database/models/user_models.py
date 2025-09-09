"""
User management database models
"""

from sqlalchemy import String, DateTime, Boolean, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from app.core.database import Base

class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    GOVERNMENT_OFFICIAL = "government_official" 
    FIELD_WORKER = "field_worker"
    TRIBAL_COMMUNITY = "tribal_community"

class UserStatus(str, Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"

class User(Base):
    """User model for authentication and authorization"""
    
    __tablename__ = "users"
    
    # Basic Information
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String(15))
    
    # Role and Permissions
    role: Mapped[UserRole] = mapped_column(String(50), nullable=False, default=UserRole.TRIBAL_COMMUNITY)
    status: Mapped[UserStatus] = mapped_column(String(50), nullable=False, default=UserStatus.PENDING_APPROVAL)
    permissions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Location and Assignment
    state: Mapped[Optional[str]] = mapped_column(String(50))
    district: Mapped[Optional[str]] = mapped_column(String(100))
    block: Mapped[Optional[str]] = mapped_column(String(100))
    village: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Profile Information
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    department: Mapped[Optional[str]] = mapped_column(String(100))
    designation: Mapped[Optional[str]] = mapped_column(String(100))
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Authentication
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    account_locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Preferences
    language_preference: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    notification_preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Relationships
    user_sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="user")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}', state='{self.state}')>"

class UserSession(Base):
    """User session tracking"""
    
    __tablename__ = "user_sessions"
    
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    # Session Details
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    device_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Timestamps
    login_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    logout_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Status
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_sessions")

class AuditLog(Base):
    """Audit log for tracking user actions"""
    
    __tablename__ = "audit_logs"
    
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Action Details
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Request Details
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    
    # Data
    request_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    response_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Result
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Performance
    processing_time_ms: Mapped[Optional[float]] = mapped_column(Integer)
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

class Permission(Base):
    """System permissions"""
    
    __tablename__ = "permissions"
    
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Scope
    scope_level: Mapped[str] = mapped_column(String(20), nullable=False)  # system, state, district, village
    scope_values: Mapped[Optional[List[str]]] = mapped_column(JSON)  # specific values for scope
    
class RolePermission(Base):
    """Role-Permission mapping"""
    
    __tablename__ = "role_permissions"
    
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    permission_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)
    
    # Constraints
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # Additional conditions for permission

class UserNotification(Base):
    """User notifications"""
    
    __tablename__ = "user_notifications"
    
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Notification Details
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="normal")  # low, normal, high, urgent
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Action
    action_url: Mapped[Optional[str]] = mapped_column(String(500))
    action_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Scheduling
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Metadata
    source: Mapped[str] = mapped_column(String(50), default="system")
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)