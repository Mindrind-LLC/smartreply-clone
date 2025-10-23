import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Meta API Configuration
    META_API_TOKEN: str = os.getenv("META_API_TOKEN", "")
    PAGE_ACCESS_TOKEN: str = os.getenv("PAGE_ACCESS_TOKEN", "")
    
    # LLM Configuration
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")  # "openai" or "google"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./comments.db")
    
    # Meta GraphQL API
    META_GRAPHQL_BASE_URL: str = "https://graph.facebook.com/v19.0"
    
    # Few-shot examples for DM generation
    DM_EXAMPLES = [
        {
            "comment": "I need help with my assignment",
            "intent": "interested_in_services",
            "dm_message": "Hi! 👋 I'd love to help you with your assignment. Let me DM you some details about our academic support services."
        },
        {
            "comment": "How much do you charge?",
            "intent": "interested_in_services", 
            "dm_message": "Hi! Thanks for your interest! 💰 I'll send you our pricing details via DM right away."
        },
        {
            "comment": "Do you offer tutoring?",
            "intent": "interested_in_services",
            "dm_message": "Hi! Yes, we do offer tutoring services! 📚 Let me DM you all the details about our tutoring programs."
        },
        {
            "comment": "Sounds good",
            "intent": "interested_in_services",
            "dm_message": "Hi! 👋 Thanks for your comment! I'll DM you the details shortly."
        }
    ]


settings = Settings()
