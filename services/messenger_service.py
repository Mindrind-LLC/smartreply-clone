import logging
import re
from typing import Optional, Tuple, List, Dict, Any

import requests

from core.config import settings
from models.webhook_models import MetaApiResponse
from services.meta_api_client import MetaApiClient
from services.intent_analyzer import IntentAnalyzer
from services.database_service import DatabaseService
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from core.prompts import get_messaging_system_prompt


logger = logging.getLogger(__name__)

PHONE_REGEX = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")


class MessengerService:
    """Encapsulates Messenger conversation, history, and send APIs.

    High-level helpers for:
      1) Finding conversation by PSID (fallback by Page).
      2) Fetching recent messages and mapping roles (agent/user).
      3) Sending replies via /me/messages with messaging_type=RESPONSE.
    """

    def __init__(self, client: Optional[MetaApiClient] = None):
        self.client = client or MetaApiClient()
        self.page_access_token = settings.PAGE_ACCESS_TOKEN
        self.analyzer = IntentAnalyzer()
        self.db_service = DatabaseService()

    # ---- Conversations ----
    def get_conversations_by_psid(self, psid: str) -> Dict[str, Any]:
        url = f"https://graph.facebook.com/v24.0/{psid}/conversations"
        params = {
            "fields": "id,link,updated_time,participants",
        }
        headers = {"Authorization": f"Bearer {self.page_access_token}"}
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise ValueError(f"Conversations (by PSID) error: {resp.status_code} - {resp.text}")
        return resp.json()

    def get_conversations_by_page(self, page_id: str, limit: int = 25) -> Dict[str, Any]:
        url = f"https://graph.facebook.com/v24.0/{page_id}/conversations"
        params = {
            "fields": "id,link,updated_time,participants",
            "limit": str(limit),
        }
        headers = {"Authorization": f"Bearer {self.page_access_token}"}
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise ValueError(f"Conversations (by Page) error: {resp.status_code} - {resp.text}")
        return resp.json()

    def find_conversation_id(self, psid: str, page_id: str) -> Optional[str]:
        """Try PSID conversations first; fallback to page conversations."""
        try:
            data = self.get_conversations_by_psid(psid)
            convs = data.get("data", [])
            if convs:
                # pick the most recent one
                return convs[0].get("id")
        except Exception as e:
            logger.warning(f"PSID conversations lookup failed: {str(e)}")

        # Fallback by page
        data = self.get_conversations_by_page(page_id)
        for c in data.get("data", []):
            participants = (c.get("participants") or {}).get("data", [])
            if any(str(p.get("id")) == str(psid) for p in participants):
                return c.get("id")
        return None

    # ---- Messages ----
    def get_messages(self, conversation_id: str, limit: int = 25) -> Dict[str, Any]:
        url = f"https://graph.facebook.com/v24.0/{conversation_id}/messages"
        params = {
            "fields": "message,from,to,created_time",
            "limit": str(limit),
        }
        headers = {"Authorization": f"Bearer {self.page_access_token}"}
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise ValueError(f"Messages error: {resp.status_code} - {resp.text}")
        return resp.json()

    @staticmethod
    def format_messages_with_roles(messages_payload: Dict[str, Any], page_id: str) -> List[Dict[str, Any]]:
        items = messages_payload.get("data", []) if isinstance(messages_payload, dict) else []
        formatted: List[Dict[str, Any]] = []
        for m in items:
            text = m.get("message")
            from_obj = m.get("from") or {}
            from_id = str(from_obj.get("id")) if from_obj else None
            role = "agent" if from_id == str(page_id) else "user"
            formatted.append({
                "role": role,
                "text": text,
                "from_id": from_id,
                "created_time": m.get("created_time")
            })
        return formatted

    @staticmethod
    def extract_phone_number(text: str) -> Optional[str]:
        """Extract a probable phone number from free text."""
        if not text:
            return None
        match = PHONE_REGEX.search(text)
        if not match:
            return None

        raw_number = match.group(1)
        digits = re.sub(r"\D", "", raw_number)
        if len(digits) < 7:
            return None

        normalized = digits
        if raw_number.strip().startswith("+"):
            normalized = f"+{digits}"
        return normalized

    # ---- Send ----
    def send_message_response(self, psid: str, text: str) -> MetaApiResponse:
        # Validate token before sending
        self.client.validate_page_access_token(self.page_access_token)
        url = "https://graph.facebook.com/v24.0/me/messages"
        headers = {
            "Authorization": f"Bearer {self.page_access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "recipient": {"id": psid},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return MetaApiResponse(success=True, message_id=data.get("message_id") or data.get("id"))
        return MetaApiResponse(success=False, error=f"Send message error: {resp.status_code} - {resp.text}")

    # ---- Orchestration ----
    @staticmethod
    def should_process_message_event(event: Dict[str, Any], page_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Return (should_process, psid, text).

        - Only process if event has message.text
        - Skip if sender.id == page_id (self messages)
        """
        sender_id = ((event.get("sender") or {}).get("id"))
        msg = event.get("message") or {}
        text = msg.get("text")
        if not text:
            return False, None, None
        if str(sender_id) == str(page_id):
            return False, None, None
        return True, str(sender_id), str(text)

    def handle_incoming_message(self, page_id: str, psid: str, text: str, db=None) -> MetaApiResponse:
        """Fetch conversation, recent messages, and send a simple response.

        Note: This is a minimal orchestrator — you can plug in the LLM here for richer replies.
        """
        # Guard: reply only when text exists
        if not text:
            return MetaApiResponse(success=False, error="No text to reply to")
        # Resolve conversation
        conv_id = self.find_conversation_id(psid, page_id)
        if not conv_id:
            logger.warning(f"No conversation found for PSID={psid} page_id={page_id}; sending direct response")
            return self.send_message_response(psid, text)

        # Fetch and format history for context
        history = self.get_messages(conv_id, limit=25)
        formatted = self.format_messages_with_roles(history, page_id)
        logger.info(f"Loaded {len(formatted)} messages for context")

        # Persist latest user message
        phone_number = self.extract_phone_number(text)

        if db is not None:
            try:
                self.db_service.add_chat_message(db, page_id=page_id, psid=psid, role="user", text=text)
            except Exception:
                logger.exception("Failed to store incoming user message")
            try:
                chat = self.db_service.upsert_chat_record(
                    db,
                    page_id=page_id,
                    psid=psid,
                    phone_number=phone_number,
                    last_message=text,
                )
                if phone_number:
                    logger.info(
                        "Captured phone number for psid=%s (stored as %s)",
                        psid,
                        chat.phone_number,
                    )
            except Exception:
                logger.exception("Failed to upsert chat record for psid=%s", psid)

        # Build LC messages with system + history
        system_prompt = get_messaging_system_prompt()
        lc_messages = [SystemMessage(content=system_prompt)]

        if db is not None:
            # chronological order
            db_hist = self.db_service.get_chat_history(db, psid=psid, limit=25)
            for m in reversed(db_hist):
                if m.role == "agent":
                    lc_messages.append(AIMessage(content=m.text))
                else:
                    lc_messages.append(HumanMessage(content=m.text))
        else:
            # fall back to API-formatted context
            for m in reversed(formatted):
                if m.get("role") == "agent":
                    lc_messages.append(AIMessage(content=m.get("text") or ""))
                else:
                    lc_messages.append(HumanMessage(content=m.get("text") or ""))

        lc_messages.append(HumanMessage(content=text))

        try:
            llm_resp = self.analyzer.llm.invoke(lc_messages)
            reply = (llm_resp.content or "").strip() or "Thanks for your message!"
        except Exception:
            logger.exception("LLM generation failed; falling back")
            reply = "Thanks for your message! Could you share if it’s for an online class, exam, or assignment?"

        # Persist agent reply
        if db is not None:
            try:
                self.db_service.add_chat_message(db, page_id=page_id, psid=psid, role="agent", text=reply)
            except Exception:
                logger.exception("Failed to store agent reply message")

        logger.info(
            "Messenger reply prepared | psid=%s | user_message=%r | agent_reply=%r",
            psid,
            text,
            reply,
        )

        return self.send_message_response(psid, reply)
