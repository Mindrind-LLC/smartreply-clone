import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from core.config import settings
from services.comment_moderator import CommentModerator
from services.intent_analyzer import IntentAnalyzer
from services.meta_api_client import MetaApiClient
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class WebhookProcessor:
    """Service for processing Facebook webhook events"""
    
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.meta_api_client = MetaApiClient()
        self.db_service = DatabaseService()
        self.comment_moderator = CommentModerator()
    
    async def process_webhook_change(self, change, db: Session):
        """Process individual webhook change"""
        try:
            value = change.value
            
            # Check if this is a comment event
            if value.item == "comment" and value.verb == "add" and value.message:
                logger.info(f"Processing comment: {value.message[:50]}...")
                await self.process_comment(value, db)
            
            elif value.item == "comment" and value.verb == "remove":
                logger.info(f"Comment removed webhook received")
                await self.delete_comment(value, db)
            # Check if this is a reaction event (for logging)
            elif value.item == "reaction":
                logger.info(f"Processing reaction: {value.reaction_type} from {value.from_user.name}")
                # For now, we only process comments, but reactions can be logged
            else:
                logger.info(f"Unknown event: {value.item} {value.verb}")
                
        except Exception as e:
            logger.error(f"Error processing webhook change: {str(e)}")

    async def process_comment(self, value, db: Session):
        """Process a comment event"""
        try:
            # Extract comment data (normalize IDs)
            full_comment_id = value.comment_id
            full_post_id = value.post_id

            # Store only trailing parts in DB
            comment_id = full_comment_id.split('_')[-1] if full_comment_id else None
            post_id = full_post_id.split('_')[-1] if full_post_id else None
            user_id = value.from_user.id
            user_name = value.from_user.name
            message = value.message
            created_time = datetime.fromtimestamp(value.created_time) if value.created_time else datetime.utcnow()
            
            # Check if comment already exists
            existing_comment = self.db_service.get_comment_by_id(db, comment_id)
            if existing_comment:
                logger.info(f"Comment {comment_id} already processed, skipping")
                return
            
            # Create comment record in database
            comment_record = self.db_service.create_comment_record(
                db=db,
                comment_id=comment_id,
                post_id=post_id,
                user_id=user_id,
                user_name=user_name,
                message=message,
                created_time=created_time,
                raw_json=(value.model_dump() if hasattr(value, "model_dump") else value.__dict__)
            )
            
            logger.info(f"Created comment record with ID {comment_record.id}")
            
            # Analyze intent using LLM
            try:
                intent_response = self.intent_analyzer.analyze_intent_sync(message, user_name)
                # Let LLM handle greeting; no manual prefixing here
                # Update comment with intent analysis
                updated_comment = self.db_service.update_comment_with_intent(
                    db=db,
                    comment_id=comment_id,
                    intent=intent_response.intent,
                    dm_message=intent_response.dm_message if intent_response.intent in ["positive", "interested_in_services"] else None
                )
                
                logger.info(f"Intent analysis completed: {intent_response.intent}")

                should_remove, removal_reason = self.comment_moderator.should_remove_comment(
                    message, intent_response.intent
                )
                if should_remove:
                    logger.warning(
                        f"Removing harmful comment {full_comment_id} due to {removal_reason}"
                    )
                    removal_response = self.comment_moderator.delete_comment(full_comment_id)
                    if removal_response.success:
                        try:
                            self.db_service.log_deleted_comment(
                                db=db,
                                comment_id=comment_id,
                                post_id=post_id,
                                user_id=user_id,
                                user_name=user_name,
                                message=message,
                                intent=intent_response.intent,
                                comment_timestamp=created_time,
                                removal_reason=removal_reason,
                            )
                        except Exception as log_err:
                            logger.error(f"Failed to log deleted comment {comment_id}: {log_err}")
                        if comment_record:
                            self.db_service.delete_comment_by_id(db, comment_id)
                            logger.info(
                                f"Comment {comment_id} removed from Meta and database"
                            )
                        else:
                            logger.info(
                                f"Comment {comment_id} not persisted yet; skipping DB delete"
                            )
                    else:
                        logger.error(
                            f"Failed to delete comment {comment_id}: {removal_response.error}"
                        )
                    return
                
                # Send DM only for "positive" or "interested_in_services" intents
                if intent_response.intent in ["positive", "interested_in_services"] and intent_response.dm_message:
                    # Extract page_id from full post id for API call
                    page_id = (full_post_id.split('_')[0] if (full_post_id and '_' in full_post_id) else full_post_id)
                    # Meta API expects the pure comment id (without post prefix)
                    await self.send_dm_and_update_record(comment_id, intent_response.dm_message, db, page_id)
                    logger.info(f"Comment intent is '{intent_response.intent}', sending DM")
                else:
                    logger.info(f"Comment intent is '{intent_response.intent}', not sending DM (intent doesn't require DM)")
                    
            except Exception as e:
                logger.error(f"Error analyzing intent for comment {comment_id}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error processing comment: {str(e)}")

    async def send_dm_and_update_record(self, comment_id: str, dm_message: str, db: Session, page_id: str = None):
        """Send DM and update database record"""
        try:
            # Send private reply via Meta API
            api_response = self.meta_api_client.send_private_reply_sync(comment_id, dm_message, page_id)
            
            if api_response.success:
                # Mark DM as sent in database
                self.db_service.mark_dm_sent(db, comment_id, api_response.message_id)
                logger.info(f"DM sent successfully to comment {comment_id}")
            else:
                logger.error(f"Failed to send DM to comment {comment_id}: {api_response.error}")
                
        except Exception as e:
            logger.error(f"Error sending DM for comment {comment_id}: {str(e)}")
    
    async def delete_comment(self, value, db: Session):
        """Delete comment from database when removed webhook is received"""
        try:
            # Extract comment_id from webhook
            full_comment_id = value.comment_id
            full_post_id = value.post_id
            post_id = full_post_id.split('_')[-1] if full_post_id else None

            # Store only trailing parts in DB
            comment_id = full_comment_id.split('_')[-1] if full_comment_id else None
            
            if not comment_id:
                logger.warning(f"No comment_id found in remove webhook")
                return

            existing_comment = self.db_service.get_comment_by_id(db, comment_id)
            if existing_comment:
                self.db_service.delete_comment_by_id(db, comment_id)
                logger.info(f"Comment {comment_id} deleted from database due to webhook remove")
                return

            logger.info(f"Comment {comment_id} not found in database; likely removed before persistence")
                
        except Exception as e:
            logger.error(f"Error deleting comment: {str(e)}")
