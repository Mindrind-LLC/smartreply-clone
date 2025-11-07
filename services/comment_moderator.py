import logging
from typing import Optional, Tuple

import requests

from core.config import settings
from models.webhook_models import MetaApiResponse

logger = logging.getLogger(__name__)


class CommentModerator:
    """
    Detects harmful comments and removes them from Facebook via the Graph API.
    """

    def __init__(self):
        if not settings.PAGE_ACCESS_TOKEN:
            raise ValueError("PAGE_ACCESS_TOKEN is required to remove comments")

        self.page_access_token = settings.PAGE_ACCESS_TOKEN
        self.keywords = [kw.lower() for kw in settings.HARMFUL_COMMENT_KEYWORDS]
        self.graph_api_root = self._build_api_root()

    def _build_api_root(self) -> str:
        base_url = settings.META_GRAPHQL_BASE_URL.rstrip("/")
        version = settings.META_GRAPH_API_VERSION.strip("/")
        return f"{base_url}/{version}" if version else base_url

    def _detect_keyword(self, message: Optional[str]) -> Optional[str]:
        if not message:
            return None
        lowered = message.lower()
        for keyword in self.keywords:
            if keyword and keyword in lowered:
                return keyword
        return None

    def should_remove_comment(self, message: str, intent: Optional[str] = None) -> Tuple[bool, str]:
        """
        Remove comments only when the LLM labels them as negative.
        Keywords are logged in the removal reason but do not trigger deletion.
        """
        if intent and intent.lower() == "negative":
            keyword = self._detect_keyword(message)
            reason = "intent:negative"
            if keyword:
                reason = f"{reason}_keyword:{keyword}"
            return True, reason
        return False, ""

    def delete_comment(self, full_comment_id: Optional[str]) -> MetaApiResponse:
        """
        Remove a comment from Facebook using the Graph API DELETE endpoint.
        """
        if not full_comment_id:
            return MetaApiResponse(success=False, error="Missing comment id")

        url = f"{self.graph_api_root}/{full_comment_id}"
        headers = {"Authorization": f"Bearer {self.page_access_token}"}

        try:
            logger.info(f"Deleting comment {full_comment_id} via Meta Graph API")
            response = requests.delete(url, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json() if response.content else {}
                success = data.get("success", True)
                if success:
                    logger.info(f"Comment {full_comment_id} removed successfully")
                    return MetaApiResponse(success=True, message_id=None, error=None)
                logger.error(f"Comment deletion reported failure: {data}")
                return MetaApiResponse(success=False, error=str(data))

            error_msg = f"Meta API delete error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return MetaApiResponse(success=False, error=error_msg)

        except requests.RequestException as exc:
            error_msg = f"Request exception deleting comment: {str(exc)}"
            logger.error(error_msg)
            return MetaApiResponse(success=False, error=error_msg)
