from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.database import get_db
from app.models import user as user_models
from app.models import visitor as visitor_models
from app.models import visit_request as visit_request_models
from app.models import notification as notification_models
from app.models import blacklist as blacklist_models
from app.schemas import user as user_schemas
from app.schemas import visitor as visitor_schemas
from app.schemas import visit_request as visit_request_schemas
from app.schemas import notification as notification_schemas
from app.services.auth_service import get_current_user
from app.services.notification_service import create_notification, send_email_notification
from app.utils.helpers import generate_qr_code

router = APIRouter(prefix="/resident", tags=["resident"])

@router.get("/dashboard")
async def get_resident_dashboard(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get resident dashboard data"""
    if current_user.role != "resident" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only approved residents can access this endpoint."
        )
    
    # Get pending requests count
    pending_requests = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.resident_id == current_user.id,
        visit_request_models.VisitRequest.status == "pending"
    ).count()
    
    # Get today's approved visits
    today = datetime.now().date()
    today_visits = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.resident_id == current_user.id,
        visit_request_models.VisitRequest.status == "approved",
        visit_request_models.VisitRequest.visit_date == today
    ).count()
    
    # Get total visitors this month
    first_day_month = datetime.now().replace(day=1).date()
    month_visitors = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.resident_id == current_user.id,
        visit_request_models.VisitRequest.visit_date >= first_day_month,
        visit_request_models.VisitRequest.status.in_(["approved", "completed"])
    ).count()
    
    # Get recent notifications
    recent_notifications = db.query(notification_models.Notification).filter(
        notification_models.Notification.user_id == current_user.id
    ).order_by(notification_models.Notification.created_at.desc()).limit(5).all()
    
    return {
        "pending_requests": pending_requests,
        "today_visits": today_visits,
        "month_visitors": month_visitors,
        "recent_notifications": recent_notifications
    }

@router.post("/register-visitor", response_model=visit_request_schemas.VisitRequestResponse)
async def register_visitor(
    visitor_data: visitor_schemas.VisitorCreate,
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register a visitor (pre-approved by resident)"""
    if current_user.role != "resident" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only approved residents can register visitors."
        )
    
    # Check if visitor is blacklisted
    blacklisted = db.query(blacklist_models.Blacklist).filter(
        blacklist_models.Blacklist.visitor_phone == visitor_data.phone_number,
        blacklist_models.Blacklist.resident_id == current_user.id,
        blacklist_models.Blacklist.is_active == True
    ).first()
    
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This visitor is blacklisted and cannot be registered."
        )
    
    # Check if visitor already exists
    existing_visitor = db.query(visitor_models.Visitor).filter(
        visitor_models.Visitor.phone_number == visitor_data.phone_number
    ).first()
    
    if not existing_visitor:
        # Create new visitor
        new_visitor = visitor_models.Visitor(
            name=visitor_data.name,
            phone_number=visitor_data.phone_number,
            email=visitor_data.email,
            id_number=visitor_data.id_number,
            purpose=visitor_data.purpose
        )
        db.add(new_visitor)
        db.flush()
        visitor_id = new_visitor.id
    else:
        visitor_id = existing_visitor.id
    
    # Create visit request (pre-approved)
    visit_request = visit_request_models.VisitRequest(
        visitor_id=visitor_id,
        resident_id=current_user.id,
        visit_date=visitor_data.visit_date,
        visit_time=visitor_data.visit_time,
        purpose=visitor_data.purpose,
        status="approved",
        approved_at=datetime.utcnow(),
        qr_code=generate_qr_code(f"visit_{visitor_id}_{current_user.id}_{datetime.utcnow().timestamp()}")
    )
    
    db.add(visit_request)
    db.commit()
    db.refresh(visit_request)
    
    # Notify security personnel
    security_users = db.query(user_models.User).filter(
        user_models.User.role == "security",
        user_models.User.is_approved == True
    ).all()
    
    for security_user in security_users:
        await create_notification(
            db=db,
            user_id=security_user.id,
            title="New Pre-Approved Visitor",
            message=f"Visitor {visitor_data.name} has been pre-approved by resident {current_user.full_name}",
            notification_type="visitor_approved"
        )
    
    # Send email to visitor if email provided
    if visitor_data.email:
        await send_email_notification(
            to_email=visitor_data.email,
            subject="Visit Approved",
            message=f"Your visit to {current_user.full_name} on {visitor_data.visit_date} has been approved. Please show the QR code at the gate."
        )
    
    return visit_request

@router.get("/pending-requests", response_model=List[visit_request_schemas.VisitRequestResponse])
async def get_pending_requests(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all pending visit requests for the resident"""
    if current_user.role != "resident" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    pending_requests = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.resident_id == current_user.id,
        visit_request_models.VisitRequest.status == "pending"
    ).order_by(visit_request_models.VisitRequest.created_at.desc()).all()
    
    return pending_requests

@router.put("/approve-request/{request_id}")
async def approve_visit_request(
    request_id: int,
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve a visit request"""
    if current_user.role != "resident" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    visit_request = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.id == request_id,
        visit_request_models.VisitRequest.resident_id == current_user.id
    ).first()
    
    if not visit_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit request not found."
        )
    
    if visit_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request has already been processed."
        )
    
    # Update request status
    visit_request.status = "approved"
    visit_request.approved_at = datetime.utcnow()
    visit_request.qr_code = generate_qr_code(f"visit_{visit_request.visitor_id}_{current_user.id}_{datetime.utcnow().timestamp()}")
    
    db.commit()
    
    # Get visitor details
    visitor = db.query(visitor_models.Visitor).filter(
        visitor_models.Visitor.id == visit_request.visitor_id
    ).first()
    
    # Notify security personnel
    security_users = db.query(user_models.User).filter(
        user_models.User.role == "security",
        user_models.User.is_approved == True
    ).all()
    
    for security_user in security_users:
        await create_notification(
            db=db,
            user_id=security_user.id,
            title="Visit Request Approved",
            message=f"Visitor {visitor.name} has been approved by resident {current_user.full_name}",
            notification_type="visitor_approved"
        )
    
    # Send email to visitor
    if visitor.email:
        await send_email_notification(
            to_email=visitor.email,
            subject="Visit Approved",
            message=f"Your visit to {current_user.full_name} on {visit_request.visit_date} has been approved. Please show the QR code at the gate."
        )
    
    return {"message": "Visit request approved successfully"}

@router.put("/deny-request/{request_id}")
async def deny_visit_request(
    request_id: int,
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deny a visit request and blacklist the visitor"""
    if current_user.role != "resident" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    visit_request = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.id == request_id,
        visit_request_models.VisitRequest.resident_id == current_user.id
    ).first()
    
    if not visit_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit request not found."
        )
    
    if visit_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request has already been processed."
        )
    
    # Get visitor details
    visitor = db.query(visitor_models.Visitor).filter(
        visitor_models.Visitor.id == visit_request.visitor_id
    ).first()
    
    # Update request status
    visit_request.status = "denied"
    visit_request.denied_at = datetime.utcnow()
    
    # Add to blacklist
    blacklist_entry = blacklist_models.Blacklist(
        visitor_phone=visitor.phone_number,
        visitor_name=visitor.name,
        resident_id=current_user.id,
        reason="Visit request denied by resident",
        blacklisted_by=current_user.id,
        is_active=True
    )
    
    db.add(blacklist_entry)
    db.commit()
    
    # Send email to visitor
    if visitor.email:
        await send_email_notification(
            to_email=visitor.email,
            subject="Visit Request Denied",
            message=f"Your visit request to {current_user.full_name} has been denied."
        )
    
    return {"message": "Visit request denied and visitor blacklisted"}

@router.get("/visitor-history", response_model=List[visit_request_schemas.VisitRequestResponse])
async def get_visitor_history(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get visitor history for the resident"""
    if current_user.role != "resident" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    visitor_history = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.resident_id == current_user.id
    ).order_by(visit_request_models.VisitRequest.created_at.desc()).offset(offset).limit(limit).all()
    
    return visitor_history

@router.get("/notifications", response_model=List[notification_schemas.NotificationResponse])
async def get_notifications(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20
):
    """Get notifications for the resident"""
    if current_user.role != "resident" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    notifications = db.query(notification_models.Notification).filter(
        notification_models.Notification.user_id == current_user.id
    ).order_by(notification_models.Notification.created_at.desc()).limit(limit).all()
    
    return notifications

@router.put("/notifications/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int,
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    if current_user.role != "resident" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    notification = db.query(notification_models.Notification).filter(
        notification_models.Notification.id == notification_id,
        notification_models.Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found."
        )
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}