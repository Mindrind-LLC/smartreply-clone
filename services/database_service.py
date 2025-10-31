import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.database import Comment, get_db

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self):
        pass
    
    def create_comment_record(
        self,
        db: Session,
        comment_id: str,
        post_id: str,
        user_id: str,
        user_name: str,
        message: str,
        created_time: datetime,
        raw_json: Dict[Any, Any],
        intent: Optional[str] = None,
        dm_message: Optional[str] = None
    ) -> Comment:
        """
        Create a new comment record in the database
        
        Args:
            db: Database session
            comment_id: Unique comment ID from webhook
            post_id: Post ID from webhook
            user_id: User ID from webhook
            user_name: User name from webhook
            message: Comment message text
            created_time: When the comment was created
            raw_json: Full webhook data as JSON
            intent: Detected intent (optional)
            dm_message: Generated DM message (optional)
            
        Returns:
            Comment object
        """
        try:
            comment = Comment(
                comment_id=comment_id,
                post_id=post_id,
                user_id=user_id,
                user_name=user_name,
                message=message,
                created_time=created_time,
                raw_json=raw_json,
                intent=intent,
                dm_message=dm_message,
                dm_sent=False,
                created_at=datetime.utcnow()
            )
            
            db.add(comment)
            db.commit()
            db.refresh(comment)
            
            logger.info(f"Created comment record with ID {comment.id} for comment_id {comment_id}")
            return comment
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating comment record: {str(e)}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating comment record: {str(e)}")
            raise
    
    def update_comment_with_intent(
        self,
        db: Session,
        comment_id: str,
        intent: str,
        dm_message: str
    ) -> Optional[Comment]:
        """
        Update comment record with intent analysis results
        
        Args:
            db: Database session
            comment_id: Comment ID to update
            intent: Detected intent
            dm_message: Generated DM message
            
        Returns:
            Updated Comment object or None if not found
        """
        try:
            comment = db.query(Comment).filter(Comment.comment_id == comment_id).first()
            
            if not comment:
                logger.warning(f"Comment with comment_id {comment_id} not found for update")
                return None
            
            comment.intent = intent
            comment.dm_message = dm_message
            
            db.commit()
            db.refresh(comment)
            
            logger.info(f"Updated comment {comment_id} with intent: {intent}")
            return comment
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating comment {comment_id}: {str(e)}")
            raise
    
    def mark_dm_sent(
        self,
        db: Session,
        comment_id: str,
        message_id: Optional[str] = None
    ) -> Optional[Comment]:
        """
        Mark DM as sent for a comment
        
        Args:
            db: Database session
            comment_id: Comment ID to update
            message_id: Meta API message ID (optional)
            
        Returns:
            Updated Comment object or None if not found
        """
        try:
            comment = db.query(Comment).filter(Comment.comment_id == comment_id).first()
            
            if not comment:
                logger.warning(f"Comment with comment_id {comment_id} not found for DM update")
                return None
            
            comment.dm_sent = True
            comment.dm_sent_time = datetime.utcnow()
            
            db.commit()
            db.refresh(comment)
            
            logger.info(f"Marked DM as sent for comment {comment_id}")
            return comment
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error marking DM as sent for comment {comment_id}: {str(e)}")
            raise
    
    def get_comment_by_id(self, db: Session, comment_id: str) -> Optional[Comment]:
        """
        Get comment by comment_id
        
        Args:
            db: Database session
            comment_id: Comment ID to search for
            
        Returns:
            Comment object or None if not found
        """
        try:
            return db.query(Comment).filter(Comment.comment_id == comment_id).first()
        except Exception as e:
            logger.error(f"Error getting comment {comment_id}: {str(e)}")
            return None
    
    def get_comments_by_intent(self, db: Session, intent: str) -> list[Comment]:
        """
        Get all comments with specific intent
        
        Args:
            db: Database session
            intent: Intent to filter by
            
        Returns:
            List of Comment objects
        """
        try:
            return db.query(Comment).filter(Comment.intent == intent).all()
        except Exception as e:
            logger.error(f"Error getting comments by intent {intent}: {str(e)}")
            return []
    
    def get_pending_dms(self, db: Session) -> list[Comment]:
        """
        Get all comments that have DM messages but haven't been sent yet
        
        Args:
            db: Database session
            
        Returns:
            List of Comment objects with pending DMs
        """
        try:
            return db.query(Comment).filter(
                Comment.dm_message.isnot(None),
                Comment.dm_sent == False
            ).all()
        except Exception as e:
            logger.error(f"Error getting pending DMs: {str(e)}")
            return []
    
    def delete_comment_by_id(self, db: Session, comment_id: str) -> bool:
        """
        Delete comment by comment_id
        
        Args:
            db: Database session
            comment_id: Comment ID to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            comment = db.query(Comment).filter(Comment.comment_id == comment_id).first()
            
            if not comment:
                logger.warning(f"Comment with comment_id {comment_id} not found for deletion")
                return False
            
            db.delete(comment)
            db.commit()
            
            logger.info(f"Deleted comment {comment_id} from database")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting comment {comment_id}: {str(e)}")
            return False
