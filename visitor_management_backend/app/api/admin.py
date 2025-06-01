from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.visitor import Visitor
from app.models.visit_request import VisitRequest
from app.models.notification import Notification
from app.models.blacklist import BlacklistedVisitor
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.visit_request import VisitRequestResponse, DailyVisitReport
from app.utils.security import get_current_user, require_role
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.services.report_service import ReportService

router = APIRouter()
notification_service = NotificationService()
email_service = EmailService()
report_service = ReportService()

@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    try:
        # Get counts for various entities
        total_residents = db.query(User).filter(User.role == "resident").count()
        pending_residents = db.query(User).filter(
            and_(User.role == "resident", User.is_approved == False)
        ).count()
        active_residents = db.query(User).filter(
            and_(User.role == "resident", User.is_active == True, User.is_approved == True)
        ).count()
        
        total_security = db.query(User).filter(User.role == "security").count()
        
        # Visit statistics for today
        today = datetime.now().date()
        today_visits = db.query(VisitRequest).filter(
            func.date(VisitRequest.created_at) == today
        ).count()
        
        pending_visits = db.query(VisitRequest).filter(
            VisitRequest.status == "pending"
        ).count()
        
        approved_visits_today = db.query(VisitRequest).filter(
            and_(
                func.date(VisitRequest.created_at) == today,
                VisitRequest.status == "approved"
            )
        ).count()
        
        # Active visitors (checked in but not out)
        active_visitors = db.query(VisitRequest).filter(
            and_(
                VisitRequest.status == "approved",
                VisitRequest.actual_arrival_time.isnot(None),
                VisitRequest.actual_departure_time.is_(None)
            )
        ).count()
        
        # Blacklisted visitors
        blacklisted_count = db.query(BlacklistedVisitor).count()
        
        # Recent activities (last 10)
        recent_activities = db.query(VisitRequest).options(
            joinedload(VisitRequest.visitor),
            joinedload(VisitRequest.resident)
        ).order_by(desc(VisitRequest.created_at)).limit(10).all()
        
        return {
            "residents": {
                "total": total_residents,
                "pending": pending_residents,
                "active": active_residents
            },
            "security_personnel": total_security,
            "visits": {
                "today": today_visits,
                "pending": pending_visits,
                "approved_today": approved_visits_today,
                "active_visitors": active_visitors
            },
            "blacklisted_visitors": blacklisted_count,
            "recent_activities": [
                {
                    "id": activity.id,
                    "visitor_name": activity.visitor.full_name if activity.visitor else "Unknown",
                    "resident_name": activity.resident.full_name if activity.resident else "Unknown",
                    "status": activity.status,
                    "created_at": activity.created_at,
                    "purpose": activity.purpose_of_visit
                }
                for activity in recent_activities
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard data: {str(e)}"
        )

@router.get("/residents", response_model=List[UserResponse])
async def get_all_residents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status_filter: Optional[str] = Query(None, regex="^(pending|approved|active|inactive)$"),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get all residents with filtering options"""
    try:
        query = db.query(User).filter(User.role == "resident")
        
        # Apply status filter
        if status_filter == "pending":
            query = query.filter(User.is_approved == False)
        elif status_filter == "approved":
            query = query.filter(User.is_approved == True)
        elif status_filter == "active":
            query = query.filter(and_(User.is_active == True, User.is_approved == True))
        elif status_filter == "inactive":
            query = query.filter(User.is_active == False)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.full_name.ilike(search_term),
                    User.email.ilike(search_term),
                    User.phone_number.ilike(search_term),
                    User.apartment_number.ilike(search_term)
                )
            )
        
        residents = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        return [UserResponse.from_orm(resident) for resident in residents]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch residents: {str(e)}"
        )

@router.put("/residents/{resident_id}/approve")
async def approve_resident(
    resident_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Approve a resident registration"""
    try:
        resident = db.query(User).filter(
            and_(User.id == resident_id, User.role == "resident")
        ).first()
        
        if not resident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resident not found"
            )
        
        if resident.is_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resident is already approved"
            )
        
        # Approve resident
        resident.is_approved = True
        resident.is_active = True
        resident.approved_at = datetime.utcnow()
        resident.approved_by = current_user.id
        
        db.commit()
        
        # Send approval email
        try:
            await email_service.send_approval_email(
                resident.email,
                resident.full_name
            )
        except Exception as e:
            print(f"Approval email failed: {e}")
        
        # Create notification for resident
        await notification_service.create_notification(
            db=db,
            user_id=resident.id,
            title="Account Approved",
            message="Your resident account has been approved. You can now access the system.",
            notification_type="account_status",
            priority="high"
        )
        
        return {"message": "Resident approved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve resident: {str(e)}"
        )

@router.put("/residents/{resident_id}/reject")
async def reject_resident(
    resident_id: int,
    reason: str,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Reject a resident registration"""
    try:
        resident = db.query(User).filter(
            and_(User.id == resident_id, User.role == "resident")
        ).first()
        
        if not resident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resident not found"
            )
        
        if resident.is_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reject an already approved resident"
            )
        
        # Send rejection email
        try:
            await email_service.send_rejection_email(
                resident.email,
                resident.full_name,
                reason
            )
        except Exception as e:
            print(f"Rejection email failed: {e}")
        
        # Delete the resident record
        db.delete(resident)
        db.commit()
        
        return {"message": "Resident registration rejected"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject resident: {str(e)}"
        )

@router.put("/residents/{resident_id}")
async def update_resident(
    resident_id: int,
    resident_data: UserUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Update resident information"""
    try:
        resident = db.query(User).filter(
            and_(User.id == resident_id, User.role == "resident")
        ).first()
        
        if not resident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resident not found"
            )
        
        # Update fields if provided
        update_data = resident_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(resident, field):
                setattr(resident, field, value)
        
        resident.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(resident)
        
        return UserResponse.from_orm(resident)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update resident: {str(e)}"
        )

@router.delete("/residents/{resident_id}")
async def delete_resident(
    resident_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Delete a resident from the system"""
    try:
        resident = db.query(User).filter(
            and_(User.id == resident_id, User.role == "resident")
        ).first()
        
        if not resident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resident not found"
            )
        
        # Check if resident has active visits
        active_visits = db.query(VisitRequest).filter(
            and_(
                VisitRequest.resident_id == resident_id,
                VisitRequest.status.in_(["pending", "approved"]),
                VisitRequest.actual_departure_time.is_(None)
            )
        ).count()
        
        if active_visits > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete resident with active visits"
            )
        
        # Send deletion notification email
        try:
            await email_service.send_account_deletion_email(
                resident.email,
                resident.full_name
            )
        except Exception as e:
            print(f"Deletion email failed: {e}")
        
        # Delete resident
        db.delete(resident)
        db.commit()
        
        return {"message": "Resident deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resident: {str(e)}"
        )

@router.get("/visits", response_model=List[VisitRequestResponse])
async def get_all_visits(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    resident_id: Optional[int] = Query(None),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get all visit requests with filtering"""
    try:
        query = db.query(VisitRequest).options(
            joinedload(VisitRequest.visitor),
            joinedload(VisitRequest.resident),
            joinedload(VisitRequest.security_personnel)
        )
        
        # Apply filters
        if status_filter:
            query = query.filter(VisitRequest.status == status_filter)
        
        if date_from:
            query = query.filter(VisitRequest.created_at >= date_from)
        
        if date_to:
            query = query.filter(VisitRequest.created_at <= date_to)
        
        if resident_id:
            query = query.filter(VisitRequest.resident_id == resident_id)
        
        visits = query.order_by(desc(VisitRequest.created_at)).offset(skip).limit(limit).all()
        
        return [
            VisitRequestResponse(
                **visit.__dict__,
                visitor=visit.visitor.__dict__ if visit.visitor else None,
                resident=visit.resident.__dict__ if visit.resident else None,
                security_personnel=visit.security_personnel.__dict__ if visit.security_personnel else None
            )
            for visit in visits
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch visits: {str(e)}"
        )

@router.get("/reports/daily", response_model=List[DailyVisitReport])
async def get_daily_reports(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Generate daily visit reports"""
    try:
        reports = await report_service.generate_daily_reports(db, date_from, date_to)
        return reports
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate reports: {str(e)}"
        )

@router.get("/reports/export")
async def export_reports(
    report_type: str = Query(..., regex="^(daily|weekly|monthly|custom)$"),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    format: str = Query("csv", regex="^(csv|pdf|excel)$"),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Export reports in various formats"""
    try:
        file_data = await report_service.export_report(
            db, report_type, date_from, date_to, format
        )
        
        return {
            "file_data": file_data,
            "filename": f"visit_report_{report_type}_{date_from.date()}_{date_to.date()}.{format}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export report: {str(e)}"
        )

@router.get("/blacklist")
async def get_blacklisted_visitors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get all blacklisted visitors"""
    try:
        blacklisted = db.query(BlacklistedVisitor).options(
            joinedload(BlacklistedVisitor.visitor),
            joinedload(BlacklistedVisitor.resident),
            joinedload(BlacklistedVisitor.blacklisted_by_user)
        ).order_by(desc(BlacklistedVisitor.blacklisted_at)).offset(skip).limit(limit).all()
        
        return [
            {
                "id": bl.id,
                "visitor": bl.visitor.__dict__ if bl.visitor else None,
                "resident": bl.resident.__dict__ if bl.resident else None,
                "reason": bl.reason,
                "blacklisted_by": bl.blacklisted_by_user.__dict__ if bl.blacklisted_by_user else None,
                "blacklisted_at": bl.blacklisted_at
            }
            for bl in blacklisted
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch blacklisted visitors: {str(e)}"
        )

@router.delete("/blacklist/{blacklist_id}")
async def remove_from_blacklist(
    blacklist_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Remove visitor from blacklist"""
    try:
        blacklist_entry = db.query(BlacklistedVisitor).filter(
            BlacklistedVisitor.id == blacklist_id
        ).first()
        
        if not blacklist_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blacklist entry not found"
            )
        
        db.delete(blacklist_entry)
        db.commit()
        
        return {"message": "Visitor removed from blacklist successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove from blacklist: {str(e)}"
        )