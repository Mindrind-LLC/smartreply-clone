from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class WebhookUser(BaseModel):
    id: str
    name: str


class WebhookPost(BaseModel):
    status_type: Optional[str] = None
    is_published: Optional[bool] = None
    updated_time: Optional[str] = None
    permalink_url: Optional[str] = None
    promotion_status: Optional[str] = None
    id: str


class WebhookChangeValue(BaseModel):
    from_user: WebhookUser = Field(alias="from")
    post: Optional[WebhookPost] = None
    message: Optional[str] = None
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    created_time: Optional[int] = None
    item: str
    parent_id: Optional[str] = None
    verb: str
    reaction_type: Optional[str] = None


class WebhookChange(BaseModel):
    value: WebhookChangeValue
    field: str


class WebhookEntry(BaseModel):
    id: str
    time: int
    changes: List[WebhookChange]


class WebhookData(BaseModel):
    entry: List[WebhookEntry]
    object: str


class IntentAnalysisRequest(BaseModel):
    comment_message: str
    user_name: str


class IntentAnalysisResponse(BaseModel):
    intent: str = Field(description="The detected intent, e.g., 'interested_in_services'")
    dm_message: str = Field(description="The personalized DM message to send")
    confidence: Optional[float] = Field(default=None, description="Confidence score for the intent")


class MetaApiResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
