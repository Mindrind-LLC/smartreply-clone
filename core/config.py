import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Meta API Configuration
    META_API_TOKEN: str = os.getenv("META_API_TOKEN", "")
    PAGE_ACCESS_TOKEN: str = os.getenv("PAGE_ACCESS_TOKEN", "")
    META_APP_ID: str = os.getenv("META_APP_ID", "")
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    
    # LLM Configuration
    # OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")  # "openai" or "google"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./comments.db")
    
    # Meta Graph API base URL (no version segment)
    META_GRAPHQL_BASE_URL: str = "https://graph.facebook.com"
    
    DEFUALT_DM_MESSAGE: str = os.getenv(
        "DEFUALT_DM_MESSAGE",
        "Hi there! I’m Lisa. I can get you a free quote right away, could you please tell me whether you need help with an online class, exam, or assignment for your school?\n\nWhat exactly do you need help with? Online Class, Exam, Homework, Assignment, Essay Writing?"
    )
    
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
        },
        {
            "comment": "Great service, thank you!",
            "intent": "positive",
            "dm_message": "Hi! 👋 Thank you so much for your kind words! We're thrilled to hear you're happy with our service. If you need anything else, feel free to reach out!"
        },
        {
            "comment": "Amazing work, keep it up!",
            "intent": "positive",
            "dm_message": "Hi! 👋 Thank you for the positive feedback! We appreciate your support. Let us know if you need any additional help!"
        },
        {
            "comment": "Terrible service",
            "intent": "negative",
            "dm_message": ""  # No DM for negative intent
        },
        {
            "comment": "Very disappointed",
            "intent": "negative",
            "dm_message": ""  # No DM for negative intent
        },
        {
            "comment": "Nice post",
            "intent": "other",
            "dm_message": ""  # No DM for other intent
        }
    ]


settings = Settings()
