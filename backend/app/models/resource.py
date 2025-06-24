from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .node import Node

# Rest of the file remains unchanged


class ApplicationType(str, Enum):
    CONTAINER = "container"
    VM = "vm"
    SCRIPT = "script"
    OTHER = "other"


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    REMOVED = "removed"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_type: Mapped[ApplicationType] = mapped_column(
        String(50),
        nullable=False,
        default=ApplicationType.CONTAINER,
    )
    config: Mapped[JSON] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    requirements: Mapped[List["ResourceRequirement"]] = relationship(
        "ResourceRequirement",
        back_populates="application",
        cascade="all, delete-orphan",
    )
    deployments: Mapped[List["Deployment"]] = relationship(
        "Deployment", back_populates="application", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_app_owner", "owner_id"),
        Index("idx_app_name", "name"),
    )


class ResourceRequirement(Base):

    __tablename__ = "resource_requirements"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    application_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )

    cpu_cores: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    memory_gb: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    storage_gb: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    bandwidth_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    gpu_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    special_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    application: Mapped["Application"] = relationship(
        "Application", back_populates="requirements"
    )

    __table_args__ = (
        CheckConstraint("cpu_cores > 0", name="positive_cpu_cores_req"),
        CheckConstraint("memory_gb > 0", name="positive_memory_req"),
        CheckConstraint("storage_gb > 0", name="positive_storage_req"),
    )


class Deployment(Base):

    __tablename__ = "deployments"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    application_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[DeploymentStatus] = mapped_column(
        String(20), default=DeploymentStatus.PENDING, nullable=False, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stopped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    config_override: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped["Application"] = relationship(
        "Application", back_populates="deployments"
    )
    node: Mapped["Node"] = relationship("Node", back_populates="deployments")
    deployment_statuses: Mapped[List["DeploymentStatusLog"]] = relationship(
        "DeploymentStatusLog", back_populates="deployment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_deploy_node_status", "node_id", "status"),
        Index("idx_deploy_app_status", "application_id", "status"),
    )


class DeploymentStatusLog(Base):

    __tablename__ = "deployment_status_logs"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    deployment_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[DeploymentStatus] = mapped_column(String(20), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    deployment: Mapped["Deployment"] = relationship(
        "Deployment", back_populates="deployment_statuses"
    )
