from sqlalchemy import Column, String, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from .db import Base

class Lead(Base):
    __tablename__ = "leads"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    email = Column(String, index=True)
    phone = Column(String)
    company = Column(String)
    budget_min = Column(Integer)
    budget_max = Column(Integer)
    timeline = Column(String)
    authority = Column(String)      # 'dm'|'influencer'|'unknown'|'no'
    project_summary = Column(Text)
    score = Column(Integer)
    status = Column(String, default="new")  # 'hot'|'warm'|'cold'|'new'
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="lead")
