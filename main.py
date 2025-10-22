import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session

# Import our custom modules
from models.database import get_db, create_tables, Comment
from models.webhook_models import WebhookData
from services.intent_analyzer import IntentAnalyzer
from services.meta_api_client import MetaApiClient
from services.database_service import DatabaseService
from config import settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables on startup
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    create_tables()
    logger.info("Database tables created successfully")
    yield
    # Shutdown
    logger.info("Application shutting down")

# Initialize FastAPI app
app = FastAPI(title="Smart Reply Clone", version="1.0.0", lifespan=lifespan)

# Initialize services
intent_analyzer = IntentAnalyzer()
meta_api_client = MetaApiClient()
db_service = DatabaseService()

VERIFY_TOKEN = os.getenv("META_API_TOKEN")  # must match exactly what you entered in Meta dashboard

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Webhook verification endpoint for Meta"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verification successful")
        return int(challenge)  # ✅ VERY IMPORTANT — return raw challenge
    else:
        logger.warning("Webhook verification failed - token mismatch")
        return "Verification token mismatch", 403

@app.post("/webhook")
async def webhook_events(request: Request, db: Session = Depends(get_db)):
    """Main webhook handler for processing Facebook page events"""
    try:
        # Get webhook data
        data = await request.json()
        logger.info(f"Received webhook event: {json.dumps(data, indent=2)}")
        # Parse webhook data
        webhook_data = WebhookData(**data)
        
        # Process each entry in the webhook
        for entry in webhook_data.entry:
            for change in entry.changes:
                await process_webhook_change(change, db)
        
        return {"status": "received", "processed": True}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

async def process_webhook_change(change, db: Session):
    """Process individual webhook change"""
    try:
        value = change.value
        
        # Check if this is a comment event
        if value.item == "comment" and value.message:
            logger.info(f"Processing comment: {value.message[:50]}...")
            await process_comment(value, db)
        
        # Check if this is a reaction event (for logging)
        elif value.item == "reaction":
            logger.info(f"Processing reaction: {value.reaction_type} from {value.from_user.name}")
            # For now, we only process comments, but reactions can be logged
            
    except Exception as e:
        logger.error(f"Error processing webhook change: {str(e)}")

async def process_comment(value, db: Session):
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
        existing_comment = db_service.get_comment_by_id(db, comment_id)
        if existing_comment:
            logger.info(f"Comment {comment_id} already processed, skipping")
            return
        
        # Create comment record in database
        comment_record = db_service.create_comment_record(
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
            intent_response = intent_analyzer.analyze_intent_sync(message, user_name)
            
            # Update comment with intent analysis
            updated_comment = db_service.update_comment_with_intent(
                db=db,
                comment_id=comment_id,
                intent=intent_response.intent,
                dm_message=intent_response.dm_message
            )
            
            logger.info(f"Intent analysis completed: {intent_response.intent}")
            
            # Send DM if user is interested in services
            if intent_response.intent == "interested_in_services":
                # await send_dm_and_update_record(comment_id, intent_response.dm_message, db)
                logger.info(f"Comment intent is '{intent_response.intent}', sending DM")
                logger.info(f"DM message: {intent_response.dm_message}")
                logger.info(f"Comment ID: {comment_id}")
                logger.info(f"Post ID: {post_id}")
                logger.info(f"User ID: {user_id}")
                logger.info(f"User Name: {user_name}")
                logger.info(f"Created Time: {created_time}")
                logger.info(f"Raw JSON: {value.dict()}")
            else:
                logger.info(f"Comment intent is '{intent_response.intent}', not sending DM")
                
        except Exception as e:
            logger.error(f"Error analyzing intent for comment {comment_id}: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error processing comment: {str(e)}")

async def send_dm_and_update_record(comment_id: str, dm_message: str, db: Session):
    """Send DM and update database record"""
    try:
        # Send private reply via Meta API
        api_response = meta_api_client.send_private_reply_sync(comment_id, dm_message)
        
        if api_response.success:
            # Mark DM as sent in database
            db_service.mark_dm_sent(db, comment_id, api_response.message_id)
            logger.info(f"DM sent successfully to comment {comment_id}")
        else:
            logger.error(f"Failed to send DM to comment {comment_id}: {api_response.error}")
            
    except Exception as e:
        logger.error(f"Error sending DM for comment {comment_id}: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/comments")
async def get_comments(db: Session = Depends(get_db)):
    """Get all comments from database"""
    try:
        comments = db.query(Comment).order_by(Comment.created_at.desc()).limit(100).all()
        return {
            "comments": [
                {
                    "id": c.id,
                    "comment_id": c.comment_id,
                    "user_name": c.user_name,
                    "message": c.message,
                    "intent": c.intent,
                    "dm_message": c.dm_message,
                    "dm_sent": c.dm_sent,
                    "created_at": c.created_at.isoformat()
                }
                for c in comments
            ]
        }
    except Exception as e:
        logger.error(f"Error getting comments: {str(e)}")
        return {"error": str(e)}

@app.get("/comments/interested")
async def get_interested_comments(db: Session = Depends(get_db)):
    """Get comments with 'interested_in_services' intent"""
    try:
        comments = db_service.get_comments_by_intent(db, "interested_in_services")
        return {
            "interested_comments": [
                {
                    "id": c.id,
                    "comment_id": c.comment_id,
                    "user_name": c.user_name,
                    "message": c.message,
                    "dm_message": c.dm_message,
                    "dm_sent": c.dm_sent,
                    "created_at": c.created_at.isoformat()
                }
                for c in comments
            ]
        }
    except Exception as e:
        logger.error(f"Error getting interested comments: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)