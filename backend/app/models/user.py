from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .node import Node

from .base import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    CLIENT = "client"
    HOST = "host"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base):

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile info
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Accout status and role
    role: Mapped[UserRole] = mapped_column(
        String(20), nullable=False, default=UserRole.CLIENT, index=True
    )
    status: Mapped[UserStatus] = mapped_column(
        String(30), nullable=False, default=UserStatus.PENDING_VERIFICATION, index=True
    )

    # Verification and login tracking
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped["UserPreferences"] = relationship(
        "UserPreferences",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    nodes: Mapped[List["Node"]] = relationship(
        "Node", back_populates="owner", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_user_email_status", "email", "status"),
        Index("idx_user_role_status", "role", "status"),
    )


class UserSession(Base):

    __tablename__ = "user_sessions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    session_token: Mapped[UUID] = mapped_column(
        String(255), unique=True, default=uuid4, nullable=True
    )

    refresh_token: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    device_fingerprint: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Session timestamps
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now(), index=True
    )

    __table_args__ = (
        Index("idx_session_user_active", "user_id", "is_active"),
        Index("idx_session_expires", "expires_at"),
        Index("idx_session_token_active", "session_token", "is_active"),
    )


class UserPreferences(Base):

    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # UI Preferences
    theme: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=False, default="light"
    )
    language: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=False, default="en"
    )
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=False, default="UTC"
    )

    # Notification preferences
    email_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    push_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    marketing_emails: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # P2P Preferences
    auto_accept_p2p: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    max_concurrent_p2p: Mapped[int] = mapped_column(default=5, nullable=False)
    preferred_p2p_methods: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resource allocation preferences (hosts)
    max_cpu_share: Mapped[Optional[int]] = mapped_column(
        nullable=True  # Percentage 1-100
    )
    max_memory_share: Mapped[Optional[int]] = mapped_column(
        nullable=True  # Percentage 1-100
    )
    max_storage_share: Mapped[Optional[int]] = mapped_column(nullable=True)  # GB
    max_bandwidth_share: Mapped[Optional[int]] = mapped_column(nullable=True)  # Mbps

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")
