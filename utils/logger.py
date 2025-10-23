import sys
import logging

def setup_logger(name: str = "smartreply", level: int = logging.INFO) -> logging.Logger:
    """
    Setup logger with consistent formatting
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
        logger.setLevel(level)
    
    return logger

def log_webhook_event(logger: logging.Logger, event_type: str, data: dict):
    """
    Log webhook events with consistent format
    
    Args:
        logger: Logger instance
        event_type: Type of webhook event
        data: Event data
    """
    import json
    logger.info(f"🔔 WEBHOOK EVENT [{event_type}]: {json.dumps(data, indent=2)}")

def log_comment_processing(logger: logging.Logger, comment_id: str, user_name: str, message: str):
    """
    Log comment processing events
    
    Args:
        logger: Logger instance
        comment_id: Comment ID
        user_name: User name
        message: Comment message
    """
    logger.info(f"💬 PROCESSING COMMENT [{comment_id}] from {user_name}: '{message[:100]}{'...' if len(message) > 100 else ''}'")

def log_intent_analysis(logger: logging.Logger, comment_id: str, intent: str, confidence: float = None):
    """
    Log intent analysis results
    
    Args:
        logger: Logger instance
        comment_id: Comment ID
        intent: Detected intent
        confidence: Confidence score
    """
    confidence_str = f" (confidence: {confidence:.2f})" if confidence else ""
    logger.info(f"🎯 INTENT ANALYSIS [{comment_id}]: {intent}{confidence_str}")

def log_dm_sent(logger: logging.Logger, comment_id: str, dm_message: str, success: bool):
    """
    Log DM sending results
    
    Args:
        logger: Logger instance
        comment_id: Comment ID
        dm_message: DM message sent
        success: Whether DM was sent successfully
    """
    status = "✅" if success else "❌"
    logger.info(f"{status} DM SENT [{comment_id}]: '{dm_message[:50]}{'...' if len(dm_message) > 50 else ''}'")
