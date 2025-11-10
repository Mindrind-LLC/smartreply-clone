import os
import json
import logging
import asyncio
from datetime import datetime
from re import T
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session

# Import our custom modules
from models.database import get_db, create_tables, Comment, SessionLocal
from models.webhook_models import WebhookData
from services.webhook_processor import WebhookProcessor
from services.messenger_service import MessengerService
from core.config import settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Async processing queues and worker tracking
message_task_queue: Optional[asyncio.Queue] = None
comment_task_queue: Optional[asyncio.Queue] = None
worker_tasks: list[asyncio.Task] = []

# Create database tables on startup
from contextlib import asynccontextmanager


async def _messaging_worker(queue: asyncio.Queue):
    while True:
        try:
            task = await queue.get()
        except asyncio.CancelledError:
            break
        try:
            page_id = task["page_id"]
            psid = task["psid"]
            text = task["text"]

            def _run():
                db = SessionLocal()
                try:
                    messenger_service.handle_incoming_message(page_id=page_id, psid=psid, text=text, db=db)
                finally:
                    db.close()

            await asyncio.to_thread(_run)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception("Messaging worker failed for psid=%s: %s", task.get("psid"), exc)
        finally:
            queue.task_done()


async def _comment_worker(queue: asyncio.Queue):
    while True:
        try:
            change = await queue.get()
        except asyncio.CancelledError:
            break
        try:
            def _run():
                db = SessionLocal()
                try:
                    asyncio.run(webhook_processor.process_webhook_change(change, db))
                finally:
                    db.close()

            await asyncio.to_thread(_run)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.exception("Comment worker failed: %s", exc)
        finally:
            queue.task_done()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    create_tables()
    logger.info("Database tables created successfully")
    global message_task_queue, comment_task_queue, worker_tasks
    message_task_queue = asyncio.Queue()
    comment_task_queue = asyncio.Queue()
    worker_tasks = [
        asyncio.create_task(_messaging_worker(message_task_queue), name="messaging-worker"),
        asyncio.create_task(_comment_worker(comment_task_queue), name="comment-worker"),
    ]
    yield
    # Shutdown
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)
    worker_tasks = []
    message_task_queue = None
    comment_task_queue = None
    logger.info("Application shutting down")

# Initialize FastAPI app
app = FastAPI(title="Smart Reply Clone", version="1.0.0", lifespan=lifespan)

# Initialize services
webhook_processor = WebhookProcessor()
messenger_service = MessengerService()

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
async def webhook_events(request: Request):
    """Main webhook handler for processing Facebook page events"""
    try:
        # Get webhook data
        data = await request.json()
        logger.info(f"Received webhook event: {json.dumps(data, indent=2)}")
        # Branch: Messenger vs Feed webhook
        entries = data.get("entry", []) or []
        if entries and isinstance(entries, list) and entries[0].get("messaging"):
            # Handle Messenger messaging events without feed Pydantic model
            for entry in entries:
                page_id = entry.get("id")
                events = entry.get("messaging", []) or []
                for ev in events:
                    # Only process if text exists and not from our page
                    should, psid, text = messenger_service.should_process_message_event(ev, page_id)
                    if not should:
                        continue
                    if message_task_queue is None:
                        logger.warning("Message queue not ready; processing inline")
                        db = SessionLocal()
                        try:
                            messenger_service.handle_incoming_message(page_id=page_id, psid=psid, text=text, db=db)
                        except Exception as e:
                            logger.error(f"Error handling messaging event for PSID {psid}: {str(e)}")
                        finally:
                            db.close()
                    else:
                        await message_task_queue.put({"page_id": page_id, "psid": psid, "text": text})
            return {"status": "received", "processed": True}

        # Else: parse feed changes webhook data with Pydantic
        webhook_data = WebhookData(**data)
        
        # Process each entry in the webhook
        for entry in webhook_data.entry:
            # with open(f"message.json", "w") as f:
            #     json.dump(entry.model_dump(), f, indent=4)
            for change in entry.changes:
                if comment_task_queue is None:
                    logger.warning("Comment queue not ready; processing inline")
                    db = SessionLocal()
                    try:
                        await webhook_processor.process_webhook_change(change, db)
                    finally:
                        db.close()
                else:
                    await comment_task_queue.put(change)
        
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
