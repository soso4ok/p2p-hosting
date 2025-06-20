"""Node/Worker management models for P2P hosting platform."""

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
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"
    INITIALIZING = "initializing"


class NodeType(str, Enum):
    WORKER = "worker"
    COORDINATOR = "coordinator"
    HYBRID = "hybrid"


class ResourceStatus(str, Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    RESERVED = "reserved"
    UNAVAILABLE = "unavailable"


class Node(Base):
    __tablename__ = "nodes"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    # Owner relationship
    owner_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Node identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[NodeType] = mapped_column(
        String(20), default=NodeType.WORKER, nullable=False, index=True
    )

    # Network information
    public_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    private_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    port: Mapped[int] = mapped_column(Integer, default=8080, nullable=False)

    # Geographic location
    region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(3), nullable=True, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Node status and health
    status: Mapped[NodeStatus] = mapped_column(
        String(20), default=NodeStatus.INITIALIZING, nullable=False, index=True
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Version and configuration
    version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    configuration: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Registration and verification
    registration_token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="nodes")
    capabilities: Mapped[Optional["NodeCapabilities"]] = relationship(
        "NodeCapabilities",
        back_populates="node",
        cascade="all, delete-orphan",
        uselist=False,
    )
    metrics: Mapped[List["NodeMetrics"]] = relationship(
        "NodeMetrics", back_populates="node", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_node_owner_status", "owner_id", "status"),
        Index("idx_node_type_status", "node_type", "status"),
        Index("idx_node_region_status", "region", "status"),
        Index("idx_node_heartbeat", "last_heartbeat"),
        CheckConstraint("port > 0 AND port <= 65535", name="valid_port"),
    )


class NodeCapabilities(Base):
    __tablename__ = "node_capabilities"

    # Primary key (one-to-one with node)
    node_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # CPU capabilities
    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    cpu_threads: Mapped[int] = mapped_column(Integer, nullable=False)
    cpu_frequency_mhz: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cpu_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cpu_architecture: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Memory capabilities
    memory_total_gb: Mapped[float] = mapped_column(Float, nullable=False)
    memory_available_gb: Mapped[float] = mapped_column(Float, nullable=False)

    # Storage capabilities
    storage_total_gb: Mapped[float] = mapped_column(Float, nullable=False)
    storage_available_gb: Mapped[float] = mapped_column(Float, nullable=False)
    storage_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True  # SSD, HDD, NVMe
    )

    # Network capabilities
    bandwidth_upload_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bandwidth_download_mbps: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    network_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Resource allocation limits (set by owner)
    max_cpu_allocation_percent: Mapped[int] = mapped_column(
        Integer, default=80, nullable=False
    )
    max_memory_allocation_percent: Mapped[int] = mapped_column(
        Integer, default=80, nullable=False
    )
    max_storage_allocation_gb: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    max_bandwidth_allocation_mbps: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Current resource status
    resource_status: Mapped[ResourceStatus] = mapped_column(
        String(20), default=ResourceStatus.AVAILABLE, nullable=False, index=True
    )

    # Additional capabilities (JSON for flexibility)
    additional_capabilities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    node: Mapped["Node"] = relationship("Node", back_populates="capabilities")

    # Constraints
    __table_args__ = (
        CheckConstraint("cpu_cores > 0", name="positive_cpu_cores"),
        CheckConstraint("cpu_threads >= cpu_cores", name="valid_cpu_threads"),
        CheckConstraint("memory_total_gb > 0", name="positive_memory_total"),
        CheckConstraint(
            "memory_available_gb <= memory_total_gb", name="valid_memory_available"
        ),
        CheckConstraint("storage_total_gb > 0", name="positive_storage_total"),
        CheckConstraint(
            "storage_available_gb <= storage_total_gb", name="valid_storage_available"
        ),
        CheckConstraint(
            "max_cpu_allocation_percent > 0 AND max_cpu_allocation_percent <= 100",
            name="valid_cpu_allocation",
        ),
        CheckConstraint(
            "max_memory_allocation_percent > 0 AND max_memory_allocation_percent <= 100",
            name="valid_memory_allocation",
        ),
        Index("idx_capabilities_resource_status", "resource_status"),
    )


class NodeMetrics(Base):

    __tablename__ = "node_metrics"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    # Foreign key to node
    node_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Timestamp for this metric snapshot
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # CPU metrics
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_load_average: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_temperature_celsius: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Memory metrics
    memory_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_available_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Storage metrics
    storage_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storage_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storage_available_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storage_read_iops: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storage_write_iops: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Network metrics
    network_bytes_sent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    network_bytes_received: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    network_packets_sent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    network_packets_received: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    network_errors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # System metrics
    uptime_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    process_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thread_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # P2P specific metrics
    active_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Performance score (calculated metric)
    performance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Additional metrics (JSON for flexibility)
    additional_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    node: Mapped["Node"] = relationship("Node", back_populates="metrics")

    # Indexes for time-series queries
    __table_args__ = (
        Index("idx_metrics_node_timestamp", "node_id", "timestamp"),
        Index("idx_metrics_timestamp", "timestamp"),
        Index("idx_metrics_performance", "performance_score"),
        CheckConstraint(
            "cpu_usage_percent >= 0 AND cpu_usage_percent <= 100",
            name="valid_cpu_usage",
        ),
        CheckConstraint(
            "memory_usage_percent >= 0 AND memory_usage_percent <= 100",
            name="valid_memory_usage",
        ),
        CheckConstraint(
            "storage_usage_percent >= 0 AND storage_usage_percent <= 100",
            name="valid_storage_usage",
        ),
        CheckConstraint("active_tasks >= 0", name="positive_active_tasks"),
        CheckConstraint("completed_tasks >= 0", name="positive_completed_tasks"),
        CheckConstraint("failed_tasks >= 0", name="positive_failed_tasks"),
    )
