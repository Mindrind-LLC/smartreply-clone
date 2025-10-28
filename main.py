import os
import json
import logging
from datetime import datetime
from re import T
from typing import Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session

# Import our custom modules
from models.database import get_db, create_tables, Comment
from models.webhook_models import WebhookData
from services.webhook_processor import WebhookProcessor
from core.config import settings

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
webhook_processor = WebhookProcessor()

VERIFY_TOKEN = os.getenv("META_API_TOKEN")  # must match exactly what you entered in Meta dashboard

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

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
            # with open(f"{entry.changes[0].value.from_user.name}_{entry.changes[0].value.item}_{entry.changes[0].value.verb}.json", "w") as f:
            #     json.dump(entry.model_dump(), f, indent=4)
            for change in entry.changes:
                await webhook_processor.process_webhook_change(change, db)
        
        return {"status": "received", "processed": True}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/comments/pending")
async def get_pending_comments(db: Session = Depends(get_db)):
    """Get pending comments from database"""
    try:
        comments = db.query(Comment).filter(Comment.dm_sent == False).order_by(Comment.created_at.desc()).limit(100).all()
        return {
            "pending_comments": [
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
        logger.error(f"Error getting pending comments: {str(e)}")
        return {"error": str(e)}

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
        comments = webhook_processor.db_service.get_comments_by_intent(db, "interested_in_services")
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
    uvicorn.run(app, host="0.0.0.0", port=8009)