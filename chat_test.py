"""Offline Messenger chat tester.

This tool lets you simulate a Facebook Messenger conversation with Lisa from
the terminal while exercising the same database plumbing used in production:
- Incoming messages go through MessengerService.handle_incoming_message
- Phone numbers are extracted, normalised, and stored in the `chats` table
- Chat history is persisted in `chat_messages`

No outbound HTTP calls are made; messages stay local to help with QA.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

from dotenv import load_dotenv

from models.database import SessionLocal, create_tables
from models.webhook_models import MetaApiResponse
from services.messenger_service import MessengerService


class DummyMetaApiClient:
    """Minimal stand-in for MetaApiClient that skips network validation."""

    def validate_page_access_token(self, input_token: str) -> None:  # noqa: D401
        return None


class OfflineMessengerService(MessengerService):
    """MessengerService variant that avoids any external HTTP calls."""

    def __init__(self):
        self._last_reply: Optional[str] = None
        super().__init__(client=DummyMetaApiClient())

    @property
    def last_reply(self) -> str:
        return self._last_reply or ""

    def find_conversation_id(self, psid: str, page_id: str) -> Optional[str]:
        """Return a fake conversation id so the LLM flow executes."""
        return "offline-conversation"

    def get_messages(self, conversation_id: str, limit: int = 25):
        """Skip Graph API history fetch; rely solely on DB history."""
        return {"data": []}

    def send_message_response(self, psid: str, text: str) -> MetaApiResponse:
        """Capture replies locally instead of calling Meta's API."""
        self._last_reply = text
        return MetaApiResponse(success=True, message_id="offline-message-id")


def prompt(prompt_text: str) -> str:
    """Read input gracefully, handling Ctrl+C/Z."""
    try:
        return input(prompt_text)
    except (KeyboardInterrupt, EOFError):
        print("\nExiting chat.")
        raise SystemExit(0) from None


def chat_loop(service: OfflineMessengerService, user_name: str) -> None:
    """Interactive chat loop with MessengerService and SQLite persistence."""
    page_id = "TEST_PAGE"
    psid = "TEST_PSID"

    # Ensure we have a chat record with the supplied name
    db = SessionLocal()
    try:
        service.db_service.upsert_chat_record(
            db,
            page_id=page_id,
            psid=psid,
            user_name=user_name,
        )

        print("\nType messages to chat with Lisa. Type 'exit' to quit.\n")

        while True:
            user_text = prompt("You: ").strip()
            if not user_text:
                continue
            if user_text.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            service.handle_incoming_message(page_id=page_id, psid=psid, text=user_text, db=db)
            reply = service.last_reply or "(No reply generated)"
            print(f"Lisa: {reply}")

            chat_record = service.db_service.get_chat_by_psid(db, psid=psid)
            if chat_record and chat_record.phone_number:
                print(f"[Stored phone number: {chat_record.phone_number}]")
    finally:
        db.close()


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    create_tables()

    user_name = prompt("Enter the user's name (for first-name personalization): ").strip()
    if not user_name:
        user_name = "Friend"

    try:
        service = OfflineMessengerService()
    except Exception as exc:
        logging.error("Failed to initialise MessengerService: %s", exc)
        sys.exit(1)

    chat_loop(service, user_name)


if __name__ == "__main__":
    main()
