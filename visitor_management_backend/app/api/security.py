from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

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
from app.utils.helpers import verify_qr_code

router = APIRouter(prefix="/security", tags=["security"])

@router.get("/dashboard")
async def get_security_dashboard(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get security dashboard data"""
    if current_user.role != "security" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only approved security personnel can access this endpoint."
        )
    
    today = datetime.now().date()
    
    # Get today's approved visits
    approved_visits_today = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.visit_date == today,
        visit_request_models.VisitRequest.status == "approved"
    ).count()
    
    # Get today's completed visits
    completed_visits_today = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.visit_date == today,
        visit_request_models.VisitRequest.status == "completed"
    ).count()
    
    # Get pending walk-in requests
    pending_walkins = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.status == "pending",
        visit_request_models.VisitRequest.is_walk_in == True
    ).count()
    
    # Get active blacklisted visitors
    active_blacklist = db.query(blacklist_models.Blacklist).filter(
        blacklist_models.Blacklist.is_active == True
    ).count()
    
    # Get recent notifications
    recent_notifications = db.query(notification_models.Notification).filter(
        notification_models.Notification.user_id == current_user.id
    ).order_by(notification_models.Notification.created_at.desc()).limit(5).all()
    
    return {
        "approved_visits_today": approved_visits_today,
        "completed_visits_today": completed_visits_today,
        "pending_walkins": pending_walkins,
        "active_blacklist": active_blacklist,
        "recent_notifications": recent_notifications
    }

@router.post("/record-entry", response_model=visit_request_schemas.VisitRequestResponse)
async def record_walk_in_entry(
    visitor_data: visitor_schemas.VisitorWalkInCreate,
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a walk-in visitor entry"""
    if current_user.role != "security" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    # Check if visitor is blacklisted for this resident
    blacklisted = db.query(blacklist_models.Blacklist).filter(
        blacklist_models.Blacklist.visitor_phone == visitor_data.phone_number,
        blacklist_models.Blacklist.resident_id == visitor_data.resident_id,
        blacklist_models.Blacklist.is_active == True
    ).first()
    
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This visitor is blacklisted for this resident."
        )
    
    # Get resident details
    resident = db.query(user_models.User).filter(
        user_models.User.id == visitor_data.resident_id,
        user_models.User.role == "resident",
        user_models.User.is_approved == True
    ).first()
    
    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found or not approved."
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
    
    # Create visit request (walk-in)
    visit_request = visit_request_models.VisitRequest(
        visitor_id=visitor_id,
        resident_id=visitor_data.resident_id,
        visit_date=datetime.now().date(),
        visit_time=datetime.now().time(),
        purpose=visitor_data.purpose,
        status="pending",
        is_walk_in=True,
        recorded_by=current_user.id
    )
    
    db.add(visit_request)
    db.commit()
    db.refresh(visit_request)
    
    # Notify resident
    await create_notification(
        db=db,
        user_id=visitor_data.resident_id,
        title="Walk-in Visitor Request",
        message=f"Walk-in visitor {visitor_data.name} is requesting to see you. Please approve or deny.",
        notification_type="walk_in_request"
    )
    
    # Send email to resident
    if resident.email:
        await send_email_notification(
            to_email=resident.email,
            subject="Walk-in Visitor Request",
            message=f"Walk-in visitor {visitor_data.name} is at the gate requesting to see you. Please check your app to approve or deny."
        )
    
    return visit_request

@router.get("/verify-visitor/{qr_code}")
async def verify_visitor_qr(
    qr_code: str,
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify visitor using QR code"""
    if current_user.role != "security" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    # Find visit request by QR code
    visit_request = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.qr_code == qr_code,
        visit_request_models.VisitRequest.status == "approved"
    ).first()
    
    if not visit_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid QR code or visit not approved."
        )
    
    # Check if visit is for today
    if visit_request.visit_date != datetime.now().date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This visit is not scheduled for today."
        )
    
    # Get visitor and resident details
    visitor = db.query(visitor_models.Visitor).filter(
        visitor_models.Visitor.id == visit_request.visitor_id
    ).first()
    
    resident = db.query(user_models.User).filter(
        user_models.User.id == visit_request.resident_id
    ).first()
    
    return {
        "valid": True,
        "visitor": visitor,
        "resident": resident,
        "visit_request": visit_request,
        "message": "Visitor verified successfully. You may allow entry."
    }

@router.put("/complete-visit/{request_id}")
async def complete_visit(
    request_id: int,
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a visit as completed"""
    if current_user.role != "security" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    visit_request = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.id == request_id
    ).first()
    
    if not visit_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit request not found."
        )
    
    if visit_request.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visit must be approved before it can be completed."
        )
    
    # Update visit status
    visit_request.status = "completed"
    visit_request.completed_at = datetime.utcnow()
    visit_request.completed_by = current_user.id
    
    db.commit()
    
    return {"message": "Visit marked as completed"}

@router.get("/today-visits", response_model=List[visit_request_schemas.VisitRequestResponse])
async def get_today_visits(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None
):
    """Get today's visits"""
    if current_user.role != "security" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    today = datetime.now().date()
    query = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.visit_date == today
    )
    
    if status_filter:
        query = query.filter(visit_request_models.VisitRequest.status == status_filter)
    
    visits = query.order_by(visit_request_models.VisitRequest.created_at.desc()).all()
    return visits

@router.get("/pending-walkins", response_model=List[visit_request_schemas.VisitRequestResponse])
async def get_pending_walkins(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending walk-in requests"""
    if current_user.role != "security" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    pending_walkins = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.status == "pending",
        visit_request_models.VisitRequest.is_walk_in == True
    ).order_by(visit_request_models.VisitRequest.created_at.desc()).all()
    
    return pending_walkins

@router.get("/blacklist", response_model=List[dict])
async def get_blacklist(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active blacklisted visitors"""
    if current_user.role != "security" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    blacklist = db.query(blacklist_models.Blacklist).filter(
        blacklist_models.Blacklist.is_active == True
    ).order_by(blacklist_models.Blacklist.created_at.desc()).all()
    
    return blacklist

@router.get("/visitor-logs")
async def get_visitor_logs(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100
):
    """Get visitor logs with filtering"""
    if current_user.role != "security" or not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    
    query = db.query(visit_request_models.VisitRequest)
    
    if start_date:
        query = query.filter(visit_request_models.VisitRequest.visit_date >= start_date)
    
    if end_date:
        query = query.filter(visit_request_models.VisitRequest.visit_date <= end_date)
    
    logs = query.order_by(visit_request_models.VisitRequest.created_at.desc()).limit(limit).all()
    
    return logs

@router.get("/notifications", response_model=List[notification_schemas.NotificationResponse])
async def get_notifications(
    current_user: user_schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20
):
    """Get notifications for security personnel"""
    if current_user.role != "security" or not current_user.is_approved:
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
    if current_user.role != "security" or not current_user.is_approved:
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