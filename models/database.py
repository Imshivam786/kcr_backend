# models/database.py
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()

class Case(Base):
    __tablename__ = "cases"
    
    # Using PostgreSQL UUID type for better performance
    case_id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    images = relationship("Image", back_populates="case", cascade="all, delete-orphan")
    
    @property
    def image_count(self):
        return len(self.images)


class Image(Base):
    __tablename__ = "images"
    
    image_id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(UUID(as_uuid=False), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Relative path to the file
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # OCR Results
    ocr_result = Column(Text, nullable=True)  # JSON string of OCR results
    analyzed_at = Column(DateTime, nullable=True)
    
    # Relationship
    case = relationship("Case", back_populates="images")
