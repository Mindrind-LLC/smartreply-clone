import requests
import logging
from typing import Optional

from core.config import settings
from models.webhook_models import MetaApiResponse

logger = logging.getLogger(__name__)


class MetaApiClient:
    def __init__(self):
        self.base_url = settings.META_GRAPHQL_BASE_URL
        self.page_access_token = settings.PAGE_ACCESS_TOKEN
        self.app_id = settings.META_APP_ID
        self.app_secret = settings.META_APP_SECRET
        
        if not self.page_access_token:
            raise ValueError("PAGE_ACCESS_TOKEN is required for Meta API client")
        if not self.app_id or not self.app_secret:
            raise ValueError("META_APP_ID and META_APP_SECRET are required for token validation")
    
    def validate_page_access_token(self, input_token: str) -> None:
        """Validate the PAGE_ACCESS_TOKEN using Facebook debug_token API."""
        url = "https://graph.facebook.com/v24.0/debug_token"
        params = {
            "input_token": input_token,
            "access_token": f"{self.app_id}|{self.app_secret}",
        }
        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                raise ValueError(f"Token validation HTTP error: {resp.status_code} - {resp.text}")
            data = resp.json().get("data", {})
            if not data.get("is_valid", False):
                raise ValueError(f"Invalid PAGE_ACCESS_TOKEN: {data}")
        except requests.RequestException as e:
            raise ValueError(f"Failed to validate PAGE_ACCESS_TOKEN: {str(e)}") from e
    
    async def send_private_reply(self, comment_id: str, message: str, page_id: str = None) -> MetaApiResponse:
        """
        Send a private reply to a comment using Meta Graph API messages endpoint
        
        Args:
            comment_id: The ID of the comment to reply to
            message: The message to send as private reply
            page_id: The Facebook page ID (optional, can be extracted from comment_id)
            
        Returns:
            MetaApiResponse with success status and details
        """
        try:
            # Extract page_id from comment_id if not provided
            if not page_id:
                # Comment ID format is usually: {post_id}_{comment_id}
                # We need to extract the page_id from the post_id part
                if '_' in comment_id:
                    post_id = comment_id.split('_')[0]
                    page_id = post_id
                else:
                    raise ValueError("Cannot extract page_id from comment_id")
            
            url = f"{self.base_url}/{page_id}/messages"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "recipient": {
                    "comment_id": comment_id
                },
                "message": {
                    "text": message
                },
                "access_token": self.page_access_token
            }
            
            logger.info(f"Sending DM to comment {comment_id} via page {page_id}: '{message[:50]}...'")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"DM sent successfully to comment {comment_id}")
                return MetaApiResponse(
                    success=True,
                    message_id=response_data.get("id"),
                    error=None
                )
            else:
                error_msg = f"Meta API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return MetaApiResponse(
                    success=False,
                    message_id=None,
                    error=error_msg
                )
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error sending DM: {str(e)}"
            logger.error(error_msg)
            return MetaApiResponse(
                success=False,
                message_id=None,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error sending DM: {str(e)}"
            logger.error(error_msg)
            return MetaApiResponse(
                success=False,
                message_id=None,
                error=error_msg
            )
    
    def send_private_reply_sync(self, comment_id: str, message: str, page_id: str = None) -> MetaApiResponse:
        """
        Synchronous version of send_private_reply for compatibility
        """
        try:
            # Validate token before sending
            self.validate_page_access_token(self.page_access_token)
            # Extract page_id from comment_id if not provided
            if not page_id:
                # Comment ID format is usually: {post_id}_{comment_id}
                # We need to extract the page_id from the post_id part
                if '_' in comment_id:
                    post_id = comment_id.split('_')[0]
                    page_id = post_id
                else:
                    raise ValueError("Cannot extract page_id from comment_id")
            
            url = f"{self.base_url}/{page_id}/messages"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "recipient": {
                    "comment_id": comment_id
                },
                "message": {
                    "text": message
                },
                "access_token": self.page_access_token
            }
            
            logger.info(f"Sending DM to comment {comment_id} via page {page_id}: '{message[:50]}...'")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"DM sent successfully to comment {comment_id}")
                return MetaApiResponse(
                    success=True,
                    message_id=response_data.get("id"),
                    error=None
                )
            else:
                error_msg = f"Meta API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return MetaApiResponse(
                    success=False,
                    message_id=None,
                    error=error_msg
                )
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error sending DM: {str(e)}"
            logger.error(error_msg)
            return MetaApiResponse(
                success=False,
                message_id=None,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error sending DM: {str(e)}"
            logger.error(error_msg)
            return MetaApiResponse(
                success=False,
                message_id=None,
                error=error_msg
            )

if __name__ == "__main__":
    client = MetaApiClient()
    response = client.send_private_reply_sync("1234567890", "Hello, how are you?")
    print(response)
    print(response.success)
    print(response.message_id)
    print(response.error)