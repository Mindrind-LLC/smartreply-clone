import requests
import logging
from typing import Optional
from models.webhook_models import MetaApiResponse
from config import settings

logger = logging.getLogger(__name__)


class MetaApiClient:
    def __init__(self):
        self.base_url = settings.META_GRAPHQL_BASE_URL
        self.page_access_token = settings.PAGE_ACCESS_TOKEN
        
        if not self.page_access_token:
            raise ValueError("PAGE_ACCESS_TOKEN is required for Meta API client")
    
    async def send_private_reply(self, comment_id: str, message: str) -> MetaApiResponse:
        """
        Send a private reply to a comment using Meta GraphQL API
        
        Args:
            comment_id: The ID of the comment to reply to
            message: The message to send as private reply
            
        Returns:
            MetaApiResponse with success status and details
        """
        try:
            url = f"{self.base_url}/{comment_id}/private_replies"
            
            headers = {
                "Authorization": f"Bearer {self.page_access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "message": message
            }
            
            logger.info(f"Sending private reply to comment {comment_id}: '{message[:50]}...'")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Private reply sent successfully to comment {comment_id}")
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
            error_msg = f"Request error sending private reply: {str(e)}"
            logger.error(error_msg)
            return MetaApiResponse(
                success=False,
                message_id=None,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error sending private reply: {str(e)}"
            logger.error(error_msg)
            return MetaApiResponse(
                success=False,
                message_id=None,
                error=error_msg
            )
    
    def send_private_reply_sync(self, comment_id: str, message: str) -> MetaApiResponse:
        """
        Synchronous version of send_private_reply for compatibility
        """
        try:
            url = f"{self.base_url}/{comment_id}/private_replies"
            
            headers = {
                "Authorization": f"Bearer {self.page_access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "message": message
            }
            
            logger.info(f"Sending private reply to comment {comment_id}: '{message[:50]}...'")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Private reply sent successfully to comment {comment_id}")
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
            error_msg = f"Request error sending private reply: {str(e)}"
            logger.error(error_msg)
            return MetaApiResponse(
                success=False,
                message_id=None,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error sending private reply: {str(e)}"
            logger.error(error_msg)
            return MetaApiResponse(
                success=False,
                message_id=None,
                error=error_msg
            )
