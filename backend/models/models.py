from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    lectures = relationship("Lecture", back_populates="owner")

class Lecture(Base):
    __tablename__ = "lectures"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_url = Column(String)
    title = Column(String)
    transcript = Column(Text)
    duration_sec = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="lectures")
    notes = relationship("Note", back_populates="lecture", uselist=False)
    quizzes = relationship("Quiz", back_populates="lecture", uselist=False)

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    content_markdown = Column(Text)
    diagrams = Column(Text) # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    lecture = relationship("Lecture", back_populates="notes")

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    questions = Column(Text) # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    lecture = relationship("Lecture", back_populates="quizzes")

class ChatLog(Base):
    __tablename__ = "chat_logs"
    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

