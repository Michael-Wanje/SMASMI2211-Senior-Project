from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from app.models.visitor import Visitor
from app.models.visit_request import VisitRequest
from app.models.user import User
from app.models.blacklist import Blacklist
from app.models.notification import Notification
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_daily_visitor_report(self, date: datetime = None) -> Dict[str, Any]:
        """Generate daily visitor report"""
        try:
            target_date = date or datetime.utcnow().date()
            start_date = datetime.combine(target_date, datetime.min.time())
            end_date = datetime.combine(target_date, datetime.max.time())

            # Total visitors for the day
            total_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_date,
                    VisitRequest.created_at <= end_date
                )).count()

            # Approved visitors
            approved_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_date,
                    VisitRequest.created_at <= end_date,
                    VisitRequest.status == "approved"
                )).count()

            # Denied visitors
            denied_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_date,
                    VisitRequest.created_at <= end_date,
                    VisitRequest.status == "denied"
                )).count()

            # Pending visitors
            pending_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_date,
                    VisitRequest.created_at <= end_date,
                    VisitRequest.status == "pending"
                )).count()

            # Visitors by hour
            hourly_data = defaultdict(int)
            visit_requests = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_date,
                    VisitRequest.created_at <= end_date
                )).all()

            for request in visit_requests:
                hour = request.created_at.hour
                hourly_data[hour] += 1

            # Most active residents
            resident_activity = self.db.query(
                User.full_name,
                func.count(VisitRequest.id).label('visit_count')
            ).join(VisitRequest, User.id == VisitRequest.resident_id)\
            .filter(and_(
                VisitRequest.created_at >= start_date,
                VisitRequest.created_at <= end_date
            )).group_by(User.id, User.full_name)\
            .order_by(desc('visit_count'))\
            .limit(5).all()

            return {
                "date": target_date.isoformat(),
                "summary": {
                    "total_visitors": total_visitors,
                    "approved_visitors": approved_visitors,
                    "denied_visitors": denied_visitors,
                    "pending_visitors": pending_visitors,
                    "approval_rate": round((approved_visitors / total_visitors * 100) if total_visitors > 0 else 0, 2)
                },
                "hourly_distribution": dict(hourly_data),
                "top_residents": [
                    {"name": name, "visit_count": count} 
                    for name, count in resident_activity
                ]
            }
        except Exception as e:
            logger.error(f"Error generating daily visitor report: {str(e)}")
            raise

    def get_weekly_visitor_report(self, start_date: datetime = None) -> Dict[str, Any]:
        """Generate weekly visitor report"""
        try:
            if start_date is None:
                start_date = datetime.utcnow().date() - timedelta(days=6)
            else:
                start_date = start_date.date() if isinstance(start_date, datetime) else start_date

            end_date = start_date + timedelta(days=6)
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Daily breakdown
            daily_stats = []
            current_date = start_date

            while current_date <= end_date:
                day_start = datetime.combine(current_date, datetime.min.time())
                day_end = datetime.combine(current_date, datetime.max.time())

                day_total = self.db.query(VisitRequest)\
                    .filter(and_(
                        VisitRequest.created_at >= day_start,
                        VisitRequest.created_at <= day_end
                    )).count()

                day_approved = self.db.query(VisitRequest)\
                    .filter(and_(
                        VisitRequest.created_at >= day_start,
                        VisitRequest.created_at <= day_end,
                        VisitRequest.status == "approved"
                    )).count()

                daily_stats.append({
                    "date": current_date.isoformat(),
                    "total_visitors": day_total,
                    "approved_visitors": day_approved,
                    "approval_rate": round((day_approved / day_total * 100) if day_total > 0 else 0, 2)
                })

                current_date += timedelta(days=1)

            # Weekly totals
            total_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_datetime,
                    VisitRequest.created_at <= end_datetime
                )).count()

            approved_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_datetime,
                    VisitRequest.created_at <= end_datetime,
                    VisitRequest.status == "approved"
                )).count()

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "summary": {
                    "total_visitors": total_visitors,
                    "approved_visitors": approved_visitors,
                    "average_daily_visitors": round(total_visitors / 7, 2),
                    "overall_approval_rate": round((approved_visitors / total_visitors * 100) if total_visitors > 0 else 0, 2)
                },
                "daily_breakdown": daily_stats
            }
        except Exception as e:
            logger.error(f"Error generating weekly visitor report: {str(e)}")
            raise

    def get_monthly_visitor_report(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """Generate monthly visitor report"""
        try:
            current_date = datetime.utcnow()
            target_year = year or current_date.year
            target_month = month or current_date.month

            # Get first and last day of the month
            first_day = datetime(target_year, target_month, 1)
            if target_month == 12:
                last_day = datetime(target_year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(target_year, target_month + 1, 1) - timedelta(days=1)

            start_datetime = datetime.combine(first_day.date(), datetime.min.time())
            end_datetime = datetime.combine(last_day.date(), datetime.max.time())

            # Monthly statistics
            total_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_datetime,
                    VisitRequest.created_at <= end_datetime
                )).count()

            approved_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_datetime,
                    VisitRequest.created_at <= end_datetime,
                    VisitRequest.status == "approved"
                )).count()

            denied_visitors = self.db.query(VisitRequest)\
                .filter(and_(
                    VisitRequest.created_at >= start_datetime,
                    VisitRequest.created_at <= end_datetime,
                    VisitRequest.status == "denied"
                )).count()

            # Top visiting days
            daily_visits = self.db.query(
                func.date(VisitRequest.created_at).label('visit_date'),
                func.count(VisitRequest.id).label('visit_count')
            ).filter(and_(
                VisitRequest.created_at >= start_datetime,
                VisitRequest.created_at <= end_datetime
            )).group_by(func.date(VisitRequest.created_at))\
            .order_by(desc('visit_count'))\
            .limit(10).all()

            # Busiest hours
            hourly_visits = self.db.query(
                func.extract('hour', VisitRequest.created_at).label('hour'),
                func.count(VisitRequest.id).label('visit_count')
            ).filter(and_(
                VisitRequest.created_at >= start_datetime,
                VisitRequest.created_at <= end_datetime
            )).group_by(func.extract('hour', VisitRequest.created_at))\
            .order_by(desc('visit_count')).all()

            return {
                "period": {
                    "year": target_year,
                    "month": target_month,
                    "month_name": first_day.strftime("%B"),
                    "start_date": first_day.date().isoformat(),
                    "end_date": last_day.date().isoformat()
                },
                "summary": {
                    "total_visitors": total_visitors,
                    "approved_visitors": approved_visitors,
                    "denied_visitors": denied_visitors,
                    "approval_rate": round((approved_visitors / total_visitors * 100) if total_visitors > 0 else 0, 2),
                    "average_daily_visitors": round(total_visitors / (last_day.day), 2)
                },
                "top_visit_days": [
                    {"date": str(date), "visit_count": count} 
                    for date, count in daily_visits
                ],
                "busiest_hours": [
                    {"hour": int(hour), "visit_count": count} 
                    for hour, count in hourly_visits
                ]
            }
        except Exception as e:
            logger.error(f"Error generating monthly visitor report: {str(e)}")
            raise

    def get_blacklist_report(self) -> Dict[str, Any]:
        """Generate blacklist report"""
        try:
            # Total blacklisted visitors
            total_blacklisted = self.db.query(Blacklist).count()

            # Recent blacklists (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_blacklists = self.db.query(Blacklist)\
                .filter(Blacklist.created_at >= thirty_days_ago)\
                .count()

            # Blacklisted visitors by resident
            blacklist_by_resident = self.db.query(
                User.full_name,
                func.count(Blacklist.id).label('blacklist_count')
            ).join(Blacklist, User.id == Blacklist.resident_id)\
            .group_by(User.id, User.full_name)\
            .order_by(desc('blacklist_count')).all()

            # Recent blacklist entries
            recent_entries = self.db.query(Blacklist)\
                .join(Visitor, Blacklist.visitor_id == Visitor.id)\
                .join(User, Blacklist.resident_id == User.id)\
                .order_by(desc(Blacklist.created_at))\
                .limit(20).all()

            recent_blacklist_data = []
            for entry in recent_entries:
                recent_blacklist_data.append({
                    "visitor_name": entry.visitor.full_name,
                    "visitor_phone": entry.visitor.phone_number,
                    "resident_name": entry.resident.full_name,
                    "reason": entry.reason,
                    "created_at": entry.created_at.isoformat()
                })

            return {
                "summary": {
                    "total_blacklisted": total_blacklisted,
                    "recent_blacklists": recent_blacklists,
                    "blacklist_growth": recent_blacklists
                },
                "blacklist_by_resident": [
                    {"resident_name": name, "blacklist_count": count}
                    for name, count in blacklist_by_resident
                ],
                "recent_entries": recent_blacklist_data
            }
        except Exception as e:
            logger.error(f"Error generating blacklist report: {str(e)}")
            raise

    def get_resident_activity_report(self, resident_id: int = None) -> Dict[str, Any]:
        """Generate resident activity report"""
        try:
            query = self.db.query(User).filter(User.role == "resident")
            if resident_id:
                query = query.filter(User.id == resident_id)

            residents = query.all()
            resident_stats = []

            for resident in residents:
                # Visit requests for this resident
                total_requests = self.db.query(VisitRequest)\
                    .filter(VisitRequest.resident_id == resident.id).count()

                approved_requests = self.db.query(VisitRequest)\
                    .filter(and_(
                        VisitRequest.resident_id == resident.id,
                        VisitRequest.status == "approved"
                    )).count()

                denied_requests = self.db.query(VisitRequest)\
                    .filter(and_(
                        VisitRequest.resident_id == resident.id,
                        VisitRequest.status == "denied"
                    )).count()

                # Blacklisted visitors
                blacklisted_count = self.db.query(Blacklist)\
                    .filter(Blacklist.resident_id == resident.id).count()

                # Recent activity (last 30 days)
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                recent_activity = self.db.query(VisitRequest)\
                    .filter(and_(
                        VisitRequest.resident_id == resident.id,
                        VisitRequest.created_at >= thirty_days_ago
                    )).count()

                resident_stats.append({
                    "resident_id": resident.id,
                    "resident_name": resident.full_name,
                    "email": resident.email,
                    "total_visit_requests": total_requests,
                    "approved_requests": approved_requests,
                    "denied_requests": denied_requests,
                    "blacklisted_visitors": blacklisted_count,
                    "recent_activity": recent_activity,
                    "approval_rate": round((approved_requests / total_requests * 100) if total_requests > 0 else 0, 2)
                })

            return {
                "residents": resident_stats,
                "summary": {
                    "total_residents": len(resident_stats),
                    "active_residents": len([r for r in resident_stats if r["recent_activity"] > 0])
                }
            }
        except Exception as e:
            logger.error(f"Error generating resident activity report: {str(e)}")
            raise

    def get_security_log_report(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Generate security personnel activity report"""
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=7)
            if not end_date:
                end_date = datetime.utcnow()

            # Security recorded entries
            security_entries = self.db.query(VisitRequest)\
                .join(User, VisitRequest.recorded_by == User.id)\
                .filter(and_(
                    User.role == "security",
                    VisitRequest.created_at >= start_date,
                    VisitRequest.created_at <= end_date,
                    VisitRequest.recorded_by.isnot(None)
                )).all()

            # Group by security personnel
            security_stats = defaultdict(lambda: {
                "name": "",
                "entries_recorded": 0,
                "approved_entries": 0,
                "denied_entries": 0
            })

            for entry in security_entries:
                security_user = entry.recorded_by_user
                stats = security_stats[security_user.id]
                stats["name"] = security_user.full_name
                stats["entries_recorded"] += 1
                
                if entry.status == "approved":
                    stats["approved_entries"] += 1
                elif entry.status == "denied":
                    stats["denied_entries"] += 1

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "security_personnel": [
                    {
                        "security_id": sec_id,
                        **stats
                    }
                    for sec_id, stats in security_stats.items()
                ],
                "summary": {
                    "total_entries_recorded": sum(s["entries_recorded"] for s in security_stats.values()),
                    "total_security_active": len(security_stats)
                }
            }
        except Exception as e:
            logger.error(f"Error generating security log report: {str(e)}")
            raise

    def export_visitor_data(self, start_date: datetime, end_date: datetime, format: str = "json") -> Dict[str, Any]:
        """Export visitor data for a date range"""
        try:
            visit_requests = self.db.query(VisitRequest)\
                .join(Visitor, VisitRequest.visitor_id == Visitor.id)\
                .join(User, VisitRequest.resident_id == User.id)\
                .filter(and_(
                    VisitRequest.created_at >= start_date,
                    VisitRequest.created_at <= end_date
                )).all()

            exported_data = []
            for request in visit_requests:
                exported_data.append({
                    "visit_request_id": request.id,
                    "visitor_name": request.visitor.full_name,
                    "visitor_phone": request.visitor.phone_number,
                    "visitor_email": request.visitor.email,
                    "resident_name": request.resident.full_name,
                    "purpose": request.purpose,
                    "status": request.status,
                    "created_at": request.created_at.isoformat(),
                    "approved_at": request.approved_at.isoformat() if request.approved_at else None,
                    "recorded_by": request.recorded_by_user.full_name if request.recorded_by else "Self-registered"
                })

            return {
                "export_info": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_records": len(exported_data),
                    "format": format,
                    "generated_at": datetime.utcnow().isoformat()
                },
                "data": exported_data
            }
        except Exception as e:
            logger.error(f"Error exporting visitor data: {str(e)}")
            raise