"""
User management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.database.models.user_models import (
    User, UserSession, AuditLog, UserNotification, 
    UserRole, UserStatus
)
from app.api.auth import get_current_user, get_password_hash

router = APIRouter()

# Pydantic models for request/response
class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    status: str
    state: Optional[str] = None
    district: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: Optional[str] = None
    role: UserRole
    state: Optional[str] = None
    district: Optional[str] = None
    block: Optional[str] = None
    village: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    block: Optional[str] = None
    village: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    status: Optional[UserStatus] = None

class NotificationCreate(BaseModel):
    title: str = Field(..., max_length=200)
    message: str
    notification_type: str
    priority: str = "normal"
    action_url: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    scheduled_for: Optional[datetime] = None

class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    priority: str
    is_read: bool
    created_at: datetime
    action_url: Optional[str] = None

class UserStats(BaseModel):
    total_users: int
    active_users: int
    users_by_role: Dict[str, int]
    users_by_state: Dict[str, int]
    recent_registrations: int

# API Endpoints
@router.get("/users", response_model=List[UserInfo])
async def list_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    state: Optional[str] = None,
    district: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List users with filtering options"""
    try:
        # Check permissions
        if current_user.role.value not in ["admin", "government_official"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to list users"
            )
        
        query = select(User)
        
        # Apply role-based filtering
        if current_user.role.value == "government_official":
            # Government officials can only see users from their state
            if current_user.state:
                query = query.where(User.state == current_user.state)
        
        # Apply additional filters
        if role:
            query = query.where(User.role == role)
        if status:
            query = query.where(User.status == status)
        if state:
            query = query.where(User.state == state)
        if district:
            query = query.where(User.district == district)
        
        # Apply pagination
        query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        return [
            UserInfo(
                id=str(user.id),
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                status=user.status.value,
                state=user.state,
                district=user.district,
                created_at=user.created_at,
                last_login=user.last_login
            )
            for user in users
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )

@router.post("/users", response_model=UserInfo)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (admin only)"""
    try:
        # Check permissions
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create users"
            )
        
        # Check if username already exists
        existing_user = await db.execute(select(User).where(User.username == user_data.username))
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email = await db.execute(select(User).where(User.email == user_data.email))
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        # Create user
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            phone_number=user_data.phone_number,
            role=user_data.role,
            state=user_data.state,
            district=user_data.district,
            block=user_data.block,
            village=user_data.village,
            employee_id=user_data.employee_id,
            department=user_data.department,
            designation=user_data.designation,
            status=UserStatus.ACTIVE  # Admin-created users are active by default
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="create_user",
            resource_type="user",
            resource_id=str(new_user.id),
            method="POST",
            endpoint="/api/v1/users/users",
            status_code=201,
            success=True
        )
        db.add(audit_log)
        await db.commit()
        
        return UserInfo(
            id=str(new_user.id),
            username=new_user.username,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role.value,
            status=new_user.status.value,
            state=new_user.state,
            district=new_user.district,
            created_at=new_user.created_at,
            last_login=new_user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {str(e)}"
        )

@router.get("/users/{user_id}", response_model=UserInfo)
async def get_user_details(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a user"""
    try:
        # Check permissions
        if (current_user.role.value not in ["admin", "government_official"] and 
            str(current_user.id) != user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserInfo(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            status=user.status.value,
            state=user.state,
            district=user.district,
            created_at=user.created_at,
            last_login=user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user details: {str(e)}"
        )

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user information"""
    try:
        # Check permissions
        if (current_user.role.value not in ["admin", "government_official"] and 
            str(current_user.id) != user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        
        # Only admins can update status
        if "status" in update_data and current_user.role.value != "admin":
            del update_data["status"]
        
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        await db.commit()
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="update_user",
            resource_type="user",
            resource_id=str(user.id),
            method="PUT",
            endpoint=f"/api/v1/users/users/{user_id}",
            request_data=update_data,
            status_code=200,
            success=True
        )
        db.add(audit_log)
        await db.commit()
        
        return {"message": "User updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User update failed: {str(e)}"
        )

@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a user (soft delete)"""
    try:
        # Check permissions
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can deactivate users"
            )
        
        # Prevent self-deactivation
        if str(current_user.id) == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Deactivate user
        user.is_active = False
        user.status = UserStatus.INACTIVE
        
        # Invalidate all sessions
        sessions_result = await db.execute(
            select(UserSession).where(UserSession.user_id == user_id)
        )
        sessions = sessions_result.scalars().all()
        
        for session in sessions:
            session.is_valid = False
            session.logout_time = datetime.utcnow()
        
        await db.commit()
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="deactivate_user",
            resource_type="user",
            resource_id=str(user.id),
            method="DELETE",
            endpoint=f"/api/v1/users/users/{user_id}",
            status_code=200,
            success=True
        )
        db.add(audit_log)
        await db.commit()
        
        return {"message": "User deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User deactivation failed: {str(e)}"
        )

@router.get("/users/{user_id}/notifications", response_model=List[NotificationResponse])
async def get_user_notifications(
    user_id: str,
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user notifications"""
    try:
        # Check permissions
        if str(current_user.id) != user_id and current_user.role.value not in ["admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only access your own notifications"
            )
        
        query = select(UserNotification).where(UserNotification.user_id == user_id)
        
        if unread_only:
            query = query.where(UserNotification.is_read == False)
        
        query = query.order_by(desc(UserNotification.created_at)).limit(limit)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        return [
            NotificationResponse(
                id=str(notification.id),
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type,
                priority=notification.priority,
                is_read=notification.is_read,
                created_at=notification.created_at,
                action_url=notification.action_url
            )
            for notification in notifications
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notifications: {str(e)}"
        )

@router.post("/users/{user_id}/notifications")
async def create_notification(
    user_id: str,
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create notification for user"""
    try:
        # Check permissions
        if current_user.role.value not in ["admin", "government_official"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create notifications"
            )
        
        # Verify target user exists
        user_result = await db.execute(select(User).where(User.id == user_id))
        if not user_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found"
            )
        
        # Create notification
        notification = UserNotification(
            user_id=user_id,
            title=notification_data.title,
            message=notification_data.message,
            notification_type=notification_data.notification_type,
            priority=notification_data.priority,
            action_url=notification_data.action_url,
            action_data=notification_data.action_data,
            scheduled_for=notification_data.scheduled_for,
            source="system"
        )
        
        db.add(notification)
        await db.commit()
        
        return {"message": "Notification created successfully", "notification_id": str(notification.id)}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Notification creation failed: {str(e)}"
        )

@router.put("/users/{user_id}/notifications/{notification_id}/read")
async def mark_notification_read(
    user_id: str,
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark notification as read"""
    try:
        # Check permissions
        if str(current_user.id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only mark your own notifications as read"
            )
        
        # Get notification
        result = await db.execute(
            select(UserNotification).where(
                and_(
                    UserNotification.id == notification_id,
                    UserNotification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Mark as read
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        
        await db.commit()
        
        return {"message": "Notification marked as read"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )

@router.get("/stats", response_model=UserStats)
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics (admin only)"""
    try:
        # Check permissions
        if current_user.role.value not in ["admin", "government_official"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view user statistics"
            )
        
        # Total users
        total_result = await db.execute(select(func.count(User.id)))
        total_users = total_result.scalar()
        
        # Active users
        active_result = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_result.scalar()
        
        # Users by role
        role_result = await db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        users_by_role = {role.value: count for role, count in role_result.all()}
        
        # Users by state (apply role-based filtering)
        state_query = select(User.state, func.count(User.id)).group_by(User.state)
        if current_user.role.value == "government_official" and current_user.state:
            state_query = state_query.where(User.state == current_user.state)
        
        state_result = await db.execute(state_query)
        users_by_state = {state or "Unknown": count for state, count in state_result.all()}
        
        # Recent registrations (last 30 days)
        recent_date = datetime.utcnow() - datetime.timedelta(days=30)
        recent_result = await db.execute(
            select(func.count(User.id)).where(User.created_at >= recent_date)
        )
        recent_registrations = recent_result.scalar()
        
        return UserStats(
            total_users=total_users,
            active_users=active_users,
            users_by_role=users_by_role,
            users_by_state=users_by_state,
            recent_registrations=recent_registrations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user statistics: {str(e)}"
        )

@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs (admin only)"""
    try:
        # Check permissions
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can access audit logs"
            )
        
        query = select(AuditLog, User).outerjoin(User, AuditLog.user_id == User.id)
        
        # Apply filters
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.order_by(desc(AuditLog.created_at)).limit(limit)
        
        result = await db.execute(query)
        audit_pairs = result.all()
        
        return [
            {
                "id": str(audit_log.id),
                "user": {
                    "id": str(user.id) if user else None,
                    "username": user.username if user else None,
                    "full_name": user.full_name if user else None
                },
                "action": audit_log.action,
                "resource_type": audit_log.resource_type,
                "resource_id": audit_log.resource_id,
                "method": audit_log.method,
                "endpoint": audit_log.endpoint,
                "ip_address": audit_log.ip_address,
                "status_code": audit_log.status_code,
                "success": audit_log.success,
                "processing_time_ms": audit_log.processing_time_ms,
                "timestamp": audit_log.created_at,
                "request_data": audit_log.request_data,
                "error_message": audit_log.error_message
            }
            for audit_log, user in audit_pairs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit logs: {str(e)}"
        )