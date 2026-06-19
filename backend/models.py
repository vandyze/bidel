from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    ghazal_views = relationship("GhazalView", back_populates="user")


class OTPCode(Base):
    __tablename__ = "otp_codes"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    poem_type = Column(String, nullable=False)
    poem_id = Column(Integer, nullable=False)
    couplet_index = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookmarks")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    poem_type = Column(String, nullable=False)
    poem_id = Column(Integer, nullable=False)
    couplet_index = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notes")


class Ghazal(Base):
    __tablename__ = "ghazals"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False, index=True)
    title = Column(String, nullable=True)
    couplets = Column(JSON, nullable=False)

    keywords = relationship("GhazalKeyword", back_populates="ghazal", cascade="all, delete-orphan")
    views = relationship("GhazalView", back_populates="ghazal")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, unique=True, nullable=False, index=True)
    count = Column(Integer, nullable=True)
    percentage = Column(String, nullable=True)
    meaning = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    maqam = Column(String, nullable=True)
    contrast = Column(String, nullable=True)

    ghazals = relationship("GhazalKeyword", back_populates="keyword", cascade="all, delete-orphan")
    terjees = relationship("TerjeeKeyword", back_populates="keyword", cascade="all, delete-orphan")


class GhazalKeyword(Base):
    __tablename__ = "ghazal_keywords"

    id = Column(Integer, primary_key=True, index=True)
    ghazal_id = Column(Integer, ForeignKey("ghazals.id"), nullable=False)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    count = Column(Integer, nullable=False, default=1)

    ghazal = relationship("Ghazal", back_populates="keywords")
    keyword = relationship("Keyword", back_populates="ghazals")


class Terjee(Base):
    __tablename__ = "terjees"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False, index=True)
    couplets = Column(JSON, nullable=False)

    keywords = relationship("TerjeeKeyword", back_populates="terjee", cascade="all, delete-orphan")


class TerjeeKeyword(Base):
    __tablename__ = "terjee_keywords"

    id = Column(Integer, primary_key=True, index=True)
    terjee_id = Column(Integer, ForeignKey("terjees.id"), nullable=False)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    count = Column(Integer, nullable=False, default=1)

    terjee = relationship("Terjee", back_populates="keywords")
    keyword = relationship("Keyword", back_populates="terjees")


class GhazalView(Base):
    __tablename__ = "ghazal_views"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    ghazal_id = Column(Integer, ForeignKey("ghazals.id"), primary_key=True)
    view_count = Column(Integer, default=1)
    last_viewed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ghazal_views")
    ghazal = relationship("Ghazal", back_populates="views")


class Zand(Base):
    __tablename__ = "zand"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=True)


class Khanesh(Base):
    __tablename__ = "khanesh"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    terjee_number = Column(Integer, ForeignKey("terjees.number"), nullable=False)
    instructor = Column(String, nullable=False)
    role = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
