from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationUpdate
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(self, notification_data: NotificationCreate) -> Notification:
        """Create a new notification"""
        try:
            db_notification = Notification(**notification_data.dict())
            self.db.add(db_notification)
            self.db.commit()
            self.db.refresh(db_notification)
            logger.info(f"Notification created for user {notification_data.user_id}")
            return db_notification
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            self.db.rollback()
            raise

    def get_user_notifications(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Notification]:
        """Get all notifications for a specific user"""
        try:
            notifications = self.db.query(Notification)\
                .filter(Notification.user_id == user_id)\
                .order_by(Notification.created_at.desc())\
                .offset(skip)\
                .limit(limit)\
                .all()
            return notifications
        except Exception as e:
            logger.error(f"Error fetching notifications for user {user_id}: {str(e)}")
            raise

    def get_unread_notifications(self, user_id: int) -> List[Notification]:
        """Get unread notifications for a user"""
        try:
            notifications = self.db.query(Notification)\
                .filter(and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                ))\
                .order_by(Notification.created_at.desc())\
                .all()
            return notifications
        except Exception as e:
            logger.error(f"Error fetching unread notifications for user {user_id}: {str(e)}")
            raise

    def mark_as_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        """Mark a notification as read"""
        try:
            notification = self.db.query(Notification)\
                .filter(and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )).first()
            
            if notification:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(notification)
                logger.info(f"Notification {notification_id} marked as read")
                return notification
            return None
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            self.db.rollback()
            raise

    def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user"""
        try:
            updated_count = self.db.query(Notification)\
                .filter(and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False
                ))\
                .update({
                    "is_read": True,
                    "read_at": datetime.utcnow()
                })
            self.db.commit()
            logger.info(f"Marked {updated_count} notifications as read for user {user_id}")
            return updated_count
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            self.db.rollback()
            raise

    def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """Delete a specific notification"""
        try:
            notification = self.db.query(Notification)\
                .filter(and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )).first()
            
            if notification:
                self.db.delete(notification)
                self.db.commit()
                logger.info(f"Notification {notification_id} deleted")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            self.db.rollback()
            raise

    def get_notification_by_id(self, notification_id: int, user_id: int) -> Optional[Notification]:
        """Get a specific notification by ID"""
        try:
            notification = self.db.query(Notification)\
                .filter(and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )).first()
            return notification
        except Exception as e:
            logger.error(f"Error fetching notification {notification_id}: {str(e)}")
            raise

    def get_notifications_count(self, user_id: int, unread_only: bool = False) -> int:
        """Get count of notifications for a user"""
        try:
            query = self.db.query(Notification).filter(Notification.user_id == user_id)
            if unread_only:
                query = query.filter(Notification.is_read == False)
            return query.count()
        except Exception as e:
            logger.error(f"Error counting notifications for user {user_id}: {str(e)}")
            raise

    def create_visit_request_notification(self, resident_id: int, visitor_name: str, 
                                        visit_request_id: int, notification_type: str = "visit_request"):
        """Create notification for visit request"""
        notification_data = NotificationCreate(
            user_id=resident_id,
            title="New Visit Request",
            message=f"You have a new visit request from {visitor_name}",
            type=notification_type,
            data={
                "visit_request_id": visit_request_id,
                "visitor_name": visitor_name
            }
        )
        return self.create_notification(notification_data)

    def create_approval_notification(self, security_user_id: int, visitor_name: str, 
                                   resident_name: str, approved: bool):
        """Create notification for security when visit is approved/denied"""
        status = "approved" if approved else "denied"
        title = f"Visit Request {status.title()}"
        message = f"Visit request for {visitor_name} to see {resident_name} has been {status}"
        
        notification_data = NotificationCreate(
            user_id=security_user_id,
            title=title,
            message=message,
            type="visit_status",
            data={
                "visitor_name": visitor_name,
                "resident_name": resident_name,
                "status": status
            }
        )
        return self.create_notification(notification_data)

    def create_system_notification(self, user_id: int, title: str, message: str, 
                                 notification_type: str = "system", data: dict = None):
        """Create a system notification"""
        notification_data = NotificationCreate(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            data=data or {}
        )
        return self.create_notification(notification_data)

    def notify_all_security(self, title: str, message: str, data: dict = None):
        """Send notification to all security personnel"""
        try:
            security_users = self.db.query(User).filter(User.role == "security").all()
            notifications_created = []
            
            for user in security_users:
                notification_data = NotificationCreate(
                    user_id=user.id,
                    title=title,
                    message=message,
                    type="security_alert",
                    data=data or {}
                )
                notification = self.create_notification(notification_data)
                notifications_created.append(notification)
            
            logger.info(f"Created {len(notifications_created)} security notifications")
            return notifications_created
        except Exception as e:
            logger.error(f"Error creating security notifications: {str(e)}")
            raise

    def clean_old_notifications(self, days_old: int = 30):
        """Clean notifications older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            deleted_count = self.db.query(Notification)\
                .filter(Notification.created_at < cutoff_date)\
                .delete()
            self.db.commit()
            logger.info(f"Cleaned {deleted_count} old notifications")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning old notifications: {str(e)}")
            self.db.rollback()
            raise