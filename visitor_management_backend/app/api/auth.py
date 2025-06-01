from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import secrets

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserLogin, UserRegister, UserResponse, Token, PasswordReset, PasswordResetRequest
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.utils.security import get_current_user, verify_password, get_password_hash
from app.services.notification_service import NotificationService

router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()
email_service = EmailService()
notification_service = NotificationService()

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user (resident or security personnel)"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check phone number uniqueness
        existing_phone = db.query(User).filter(User.phone_number == user_data.phone_number).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        
        # Create new user
        new_user = User(
            email=user_data.email,
            phone_number=user_data.phone_number,
            full_name=user_data.full_name,
            password_hash=get_password_hash(user_data.password),
            role=user_data.role,
            apartment_number=user_data.apartment_number if user_data.role == "resident" else None,
            is_active=user_data.role == "security",  # Security personnel active by default
            is_approved=user_data.role == "security"  # Security personnel approved by default
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Send welcome email
        try:
            if user_data.role == "resident":
                await email_service.send_registration_confirmation(
                    user_data.email, 
                    user_data.full_name
                )
                # Notify admin about new resident registration
                admin_users = db.query(User).filter(User.role == "admin").all()
                for admin in admin_users:
                    await notification_service.create_notification(
                        db=db,
                        user_id=admin.id,
                        title="New Resident Registration",
                        message=f"{user_data.full_name} has registered as a resident and needs approval",
                        notification_type="resident_approval",
                        priority="medium",
                        data={"user_id": new_user.id, "apartment_number": user_data.apartment_number}
                    )
            else:
                await email_service.send_welcome_email(user_data.email, user_data.full_name)
        except Exception as e:
            print(f"Email sending failed: {e}")
        
        return UserResponse.from_orm(new_user)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login_user(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return access token"""
    try:
        user = db.query(User).filter(User.email == user_credentials.email).first()
        
        if not user or not verify_password(user_credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated. Please contact administrator.",
            )
        
        if user.role == "resident" and not user.is_approved:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is pending approval from administrator.",
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Generate access token
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "role": user.role}
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    try:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Generate new access token
        access_token = auth_service.create_access_token(
            data={"sub": str(current_user.id), "role": current_user.role}
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.from_orm(current_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Send password reset email"""
    try:
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a password reset link has been sent"}
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        
        db.commit()
        
        # Send reset email
        try:
            await email_service.send_password_reset_email(
                user.email, 
                user.full_name, 
                reset_token
            )
        except Exception as e:
            print(f"Password reset email failed: {e}")
        
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )

@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Reset password using reset token"""
    try:
        user = db.query(User).filter(
            User.reset_token == reset_data.token,
            User.reset_token_expires > datetime.utcnow()
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Update password
        user.password_hash = get_password_hash(reset_data.new_password)
        user.reset_token = None
        user.reset_token_expires = None
        
        db.commit()
        
        # Send confirmation email
        try:
            await email_service.send_password_change_confirmation(
                user.email, 
                user.full_name
            )
        except Exception as e:
            print(f"Password change confirmation email failed: {e}")
        
        return {"message": "Password reset successful"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.from_orm(current_user)

@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user (invalidate token on client side)"""
    try:
        # Update last activity
        current_user.last_login = datetime.utcnow()
        db.commit()
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/change-password")
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        # Verify old password
        if not verify_password(old_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password"
            )
        
        # Validate new password
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters long"
            )
        
        # Update password
        current_user.password_hash = get_password_hash(new_password)
        db.commit()
        
        # Send confirmation email
        try:
            await email_service.send_password_change_confirmation(
                current_user.email,
                current_user.full_name
            )
        except Exception as e:
            print(f"Password change confirmation email failed: {e}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.get("/verify-token")
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """Verify if token is valid"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_approved": current_user.is_approved
    }