import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

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
    
    async def process_webhook_change(self, change, db: Session):
        """Process individual webhook change"""
        try:
            value = change.value
            
            # Check if this is a comment event
            if value.item == "comment" and value.message:
                logger.info(f"Processing comment: {value.message[:50]}...")
                await self.process_comment(value, db)
            
            # Check if this is a reaction event (for logging)
            elif value.item == "reaction":
                logger.info(f"Processing reaction: {value.reaction_type} from {value.from_user.name}")
                # For now, we only process comments, but reactions can be logged
                
        except Exception as e:
            logger.error(f"Error processing webhook change: {str(e)}")

    async def process_comment(self, value, db: Session):
        """Process a comment event"""
        try:
            # Extract comment data
            comment_id = value.comment_id
            post_id = value.post_id
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
                raw_json=value.dict()
            )
            
            logger.info(f"Created comment record with ID {comment_record.id}")
            
            # Analyze intent using LLM
            try:
                intent_response = self.intent_analyzer.analyze_intent_sync(message, user_name)
                
                # Update comment with intent analysis
                updated_comment = self.db_service.update_comment_with_intent(
                    db=db,
                    comment_id=comment_id,
                    intent=intent_response.intent,
                    dm_message=intent_response.dm_message
                )
                
                logger.info(f"Intent analysis completed: {intent_response.intent}")
                
                # Send DM if user is interested in services
                if intent_response.intent == "interested_in_services":
                    # Extract page_id from post_id for the API call
                    page_id = post_id.split('_')[0] if '_' in post_id else post_id
                    await self.send_dm_and_update_record(comment_id, intent_response.dm_message, db, page_id)
                    logger.info(f"Comment intent is '{intent_response.intent}', sending DM")
                else:
                    logger.info(f"Comment intent is '{intent_response.intent}', not sending DM")
                    
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
