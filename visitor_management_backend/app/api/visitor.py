from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import user as user_models
from app.models import visitor as visitor_models
from app.models import visit_request as visit_request_models
from app.models import blacklist as blacklist_models
from app.schemas import visitor as visitor_schemas
from app.schemas import visit_request as visit_request_schemas
from app.services.notification_service import create_notification, send_email_notification

router = APIRouter(prefix="/visitor", tags=["visitor"])

@router.post("/register", response_model=visit_request_schemas.VisitRequestResponse)
async def register_visit_request(
    visit_data: visitor_schemas.VisitorRegistrationCreate,
    db: Session = Depends(get_db)
):
    """Register a new visit request"""
    
    # Validate resident exists and is approved
    resident = db.query(user_models.User).filter(
        user_models.User.id == visit_data.resident_id,
        user_models.User.role == "resident",
        user_models.User.is_approved == True
    ).first()
    
    if not resident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resident not found or not approved."
        )
    
    # Check if visitor is blacklisted for this resident
    blacklisted = db.query(blacklist_models.Blacklist).filter(
        blacklist_models.Blacklist.visitor_phone == visit_data.phone_number,
        blacklist_models.Blacklist.resident_id == visit_data.resident_id,
        blacklist_models.Blacklist.is_active == True
    ).first()
    
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are blacklisted and cannot request a visit to this resident."
        )
    
    # Check if visitor already exists
    existing_visitor = db.query(visitor_models.Visitor).filter(
        visitor_models.Visitor.phone_number == visit_data.phone_number
    ).first()
    
    if not existing_visitor:
        # Create new visitor
        new_visitor = visitor_models.Visitor(
            name=visit_data.name,
            phone_number=visit_data.phone_number,
            email=visit_data.email,
            id_number=visit_data.id_number,
            purpose=visit_data.purpose
        )
        db.add(new_visitor)
        db.flush()
        visitor_id = new_visitor.id
    else:
        visitor_id = existing_visitor.id
        # Update visitor information if provided
        if visit_data.name:
            existing_visitor.name = visit_data.name
        if visit_data.email:
            existing_visitor.email = visit_data.email
        if visit_data.id_number:
            existing_visitor.id_number = visit_data.id_number
    
    # Check for duplicate pending requests
    existing_request = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.visitor_id == visitor_id,
        visit_request_models.VisitRequest.resident_id == visit_data.resident_id,
        visit_request_models.VisitRequest.visit_date == visit_data.visit_date,
        visit_request_models.VisitRequest.status == "pending"
    ).first()
    
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending request for this date with this resident."
        )
    
    # Create visit request
    visit_request = visit_request_models.VisitRequest(
        visitor_id=visitor_id,
        resident_id=visit_data.resident_id,
        visit_date=visit_data.visit_date,
        visit_time=visit_data.visit_time,
        purpose=visit_data.purpose,
        status="pending",
        is_walk_in=False
    )
    
    db.add(visit_request)
    db.commit()
    db.refresh(visit_request)
    
    # Notify resident
    await create_notification(
        db=db,
        user_id=visit_data.resident_id,
        title="New Visit Request",
        message=f"New visit request from {visit_data.name} for {visit_data.visit_date}",
        notification_type="visit_request"
    )
    
    # Send email to resident
    if resident.email:
        await send_email_notification(
            to_email=resident.email,
            subject="New Visit Request",
            message=f"You have a new visit request from {visit_data.name} for {visit_data.visit_date}. Please check your app to approve or deny."
        )
    
    # Send confirmation email to visitor
    if visit_data.email:
        await send_email_notification(
            to_email=visit_data.email,
            subject="Visit Request Submitted",
            message=f"Your visit request to {resident.full_name} for {visit_data.visit_date} has been submitted. You will be notified once it's approved or denied."
        )
    
    return visit_request

@router.get("/status/{phone_number}")
async def get_visit_status(
    phone_number: str,
    db: Session = Depends(get_db)
):
    """Get visit status for a visitor by phone number"""
    
    # Find visitor by phone number
    visitor = db.query(visitor_models.Visitor).filter(
        visitor_models.Visitor.phone_number == phone_number
    ).first()
    
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No visitor found with this phone number."
        )
    
    # Get recent visit requests (last 30 days)
    recent_requests = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.visitor_id == visitor.id,
        visit_request_models.VisitRequest.created_at >= datetime.utcnow() - timedelta(days=30)
    ).order_by(visit_request_models.VisitRequest.created_at.desc()).all()
    
    # Get current pending requests
    pending_requests = [req for req in recent_requests if req.status == "pending"]
    
    # Get approved requests for today and future
    approved_requests = [req for req in recent_requests 
                        if req.status == "approved" and req.visit_date >= datetime.now().date()]
    
    return {
        "visitor": visitor,
        "pending_requests": pending_requests,
        "approved_requests": approved_requests,
        "recent_requests": recent_requests[:10]  # Limit to 10 most recent
    }

@router.get("/residents")
async def get_available_residents(
    db: Session = Depends(get_db)
):
    """Get list of available residents for visit requests"""
    
    residents = db.query(user_models.User).filter(
        user_models.User.role == "resident",
        user_models.User.is_approved == True,
        user_models.User.is_active == True
    ).all()
    
    # Return only necessary information
    return [
        {
            "id": resident.id,
            "full_name": resident.full_name,
            "apartment_number": resident.apartment_number
        }
        for resident in residents
    ]

@router.post("/cancel-request/{request_id}")
async def cancel_visit_request(
    request_id: int,
    phone_number: str,
    db: Session = Depends(get_db)
):
    """Cancel a pending visit request"""
    
    # Find the visit request
    visit_request = db.query(visit_request_models.VisitRequest).filter(
        visit_request_models.VisitRequest.id == request_id
    ).first()
    
    if not visit_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit request not found."
        )
    
    # Verify the visitor owns this request
    visitor = db.query(visitor_models.Visitor).filter(
        visitor_models.Visitor.id == visit_request.visitor_id,
        visitor_models.Visitor.phone_number == phone_number
    ).first()
    
    if not visitor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to cancel this request."
        )
    
    # Check if request can be cancelled
    if visit_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be cancelled."
        )
    
    # Cancel the request
    visit_request.status = "cancelled"
    visit_request.cancelled_at = datetime.utcnow()
    
    db.commit()
    
    # Notify resident about cancellation
    await create_notification(
        db=db,
        user_id=visit_request.resident_id,
        title="Visit Request Cancelled",
        message=f"Visit request from {visitor.name} for {visit_request.visit_date} has been cancelled",
        notification_type="visit_cancelled"
    )
    
    return {"message": "Visit request cancelled successfully"}

@router.get("/check-blacklist/{phone_number}/{resident_id}")
async def check_blacklist_status(
    phone_number: str,
    resident_id: int,
    db: Session = Depends(get_db)
):
    """Check if a visitor is blacklisted for a specific resident"""
    
    blacklisted = db.query(blacklist_models.Blacklist).filter(
        blacklist_models.Blacklist.visitor_phone == phone_number,
        blacklist_models.Blacklist.resident_id == resident_id,
        blacklist_models.Blacklist.is_active == True
    ).first()
    
    if blacklisted:
        return {
            "is_blacklisted": True,
            "reason": blacklisted.reason,
            "blacklisted_date": blacklisted.created_at
        }
    
    return {"is_blacklisted": False}

@router.post("/feedback")
async def submit_feedback(
    feedback_data: dict,
    db: Session = Depends(get_db)
):
    """Submit feedback about the visit experience"""
    
    # This could be expanded to store feedback in a separate table
    # For now, we'll create a notification to admin
    admin_users = db.query(user_models.User).filter(
        user_models.User.role == "admin",
        user_models.User.is_approved == True
    ).all()
    
    for admin in admin_users:
        await create_notification(
            db=db,
            user_id=admin.id,
            title="Visitor Feedback Received",
            message=f"Feedback from {feedback_data.get('visitor_name', 'Anonymous')}: {feedback_data.get('message', '')}",
            notification_type="feedback"
        )
    
    return {"message": "Thank you for your feedback"}