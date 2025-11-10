import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, Optional

import gspread
from google.oauth2 import service_account
from gspread.exceptions import WorksheetNotFound

from core.config import settings

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Append negative comment removals to Google Sheets."""

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(self) -> None:
        self._worksheet = None
        self._client = None
        self.sheet_id = settings.GOOGLE_SHEETS_SPREADSHEET_ID.strip()
        self.sheet_name = (settings.GOOGLE_SHEETS_NEGATIVE_SHEET_NAME or "").strip()
        self._credentials_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        self.enabled = bool(self.sheet_id and self._credentials_json)

        if not self.enabled:
            logger.info(
                "Google Sheets logging disabled (missing credentials or sheet id)."
            )
            return

        try:
            credentials_info = json.loads(self._credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=self.SCOPES
            )
            self._client = gspread.authorize(credentials)
            logger.info("Google Sheets client initialized")
        except Exception as exc:
            logger.error("Failed to initialize Google Sheets client: %s", exc)
            self.enabled = False

    def _get_worksheet(self):
        if not self.enabled or not self._client:
            return None

        if self._worksheet:
            return self._worksheet

        try:
            spreadsheet = self._client.open_by_key(self.sheet_id)
            print("SpreadSHeet Found")
            if self.sheet_name:
                try:
                    worksheet = spreadsheet.worksheet(self.sheet_name)
                    print("got sheet one")
                except WorksheetNotFound:
                    logger.warning(
                        "Worksheet '%s' not found. Available sheets: %s. Creating new one.",
                        self.sheet_name,
                        [ws.title for ws in spreadsheet.worksheets()],
                    )
                    worksheet = spreadsheet.add_worksheet(
                        title=self.sheet_name, rows=1000, cols=20
                    )
            else:
                worksheet = spreadsheet.sheet1

            self._worksheet = worksheet
            return worksheet

        except Exception as exc:
            logger.error(
                "Unable to access Google Sheet (id=%s, tab=%s): %r",
                self.sheet_id,
                self.sheet_name or "Sheet1",
                exc,
            )
            return None

    def append_negative_comment(self, payload: Dict[str, Any]) -> bool:
        worksheet = self._get_worksheet()
        if not worksheet:
            return False

        row = [
            payload.get("comment_id", ""),
            payload.get("post_id", ""),
            payload.get("user_id", ""),
            payload.get("user_name", ""),
            payload.get("message", ""),
            payload.get("intent", ""),
            payload.get("removal_reason", ""),
            self._format_timestamp(payload.get("comment_timestamp")),
            datetime.now(UTC).isoformat(),
        ]

        try:
            worksheet.append_row(row, value_input_option="USER_ENTERED")
            logger.info("Appended negative comment %s to Google Sheet", payload.get("comment_id"))
            return True
        except Exception as exc:
            logger.error(
                "Failed to append negative comment %s to Google Sheet: %s",
                payload.get("comment_id"),
                exc,
            )
            return False

    @staticmethod
    def _format_timestamp(value: Optional[datetime]) -> str:
        if not value:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)


if __name__ == "__main__":
    """
    Manual invocation helper:
    uv run python services/google_sheets_service.py
    """
    service = GoogleSheetsService()
    payload = {
        "comment_id": f"manual-{datetime.now(UTC).timestamp()}",
        "post_id": "test-post",
        "user_id": "test-user",
        "user_name": "Manual Runner",
        "message": "Manual sheet append test",
        "intent": "negative",
        "removal_reason": "manual_test",
        "comment_timestamp": datetime.now(UTC),
    }
    success = service.append_negative_comment(payload)
    print(
        f"Manual append {'succeeded' if success else 'failed'} "
        f"for sheet {settings.GOOGLE_SHEETS_SPREADSHEET_ID}"
    )
