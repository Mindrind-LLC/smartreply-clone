import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, JSON

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./comments.db")

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class
Base = declarative_base()


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String, unique=True, index=True, nullable=False)
    post_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_time = Column(DateTime, nullable=False)
    raw_json = Column(JSON, nullable=False)
    intent = Column(String, nullable=True)
    dm_message = Column(Text, nullable=True)
    dm_sent = Column(Boolean, default=False)
    dm_sent_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Comment(id={self.id}, comment_id='{self.comment_id}', intent='{self.intent}')>"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String, index=True, nullable=False)
    psid = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)  # 'user' | 'agent'
    text = Column(Text, nullable=False)
    created_time = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, psid='{self.psid}', role='{self.role}')>"


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String, index=True, nullable=True)
    psid = Column(String, unique=True, index=True, nullable=False)
    user_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    last_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Chat(id={self.id}, psid='{self.psid}', phone='{self.phone_number}')>"


class DeletedComment(Base):
    __tablename__ = "deleted_comments"

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(String, index=True, nullable=True)
    post_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    user_name = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    intent = Column(String, nullable=True)
    comment_timestamp = Column(DateTime, nullable=True)
    removal_reason = Column(String, nullable=True)
    removed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<DeletedComment(id={self.id}, comment_id='{self.comment_id}', intent='{self.intent}')>"


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
