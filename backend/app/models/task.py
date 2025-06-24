from datetime import datetime, timedelta
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
    from .user import User


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    TIMEOUT = "timeout"


class TaskType(str, Enum):
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"
    DATA_PROCESSING = "data_processing"
    BACKUP = "backup"
    CLEANUP = "cleanup"
    HEALTH_CHECK = "health_check"
    CUSTOM = "custom"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DependencyType(str, Enum):
    FINISH_TO_START = "finish_to_start"  # Task B starts after Task A finishes
    START_TO_START = "start_to_start"  # Task B starts when Task A starts
    FINISH_TO_FINISH = "finish_to_finish"  # Task B finishes when Task A finishes
    START_TO_FINISH = "start_to_finish"  # Task B finishes when Task A starts


class ScheduleType(str, Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    CRON = "cron"
    INTERVAL = "interval"


class Task(Base):

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(String(50), nullable=False, index=True)

    created_by: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[TaskStatus] = mapped_column(
        String(20), default=TaskStatus.PENDING, nullable=False, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        String(20), default=TaskPriority.NORMAL, nullable=False, index=True
    )

    configuration: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    environment_variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    current_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    assignee: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_to]
    )

    schedule: Mapped[Optional["TaskSchedule"]] = relationship(
        "TaskSchedule",
        back_populates="task",
        cascade="all, delete-orphan",
        uselist=False,
    )
    resource_requirements: Mapped[List["TaskResource"]] = relationship(
        "TaskResource", back_populates="task", cascade="all, delete-orphan"
    )
    executions: Mapped[List["TaskExecution"]] = relationship(
        "TaskExecution", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_task_status_priority", "status", "priority"),
        Index("idx_task_type_status", "task_type", "status"),
        Index("idx_task_creator_status", "created_by", "status"),
        Index("idx_task_scheduled_deadline", "scheduled_at", "deadline"),
        Index("idx_task_created_updated", "created_at", "updated_at"),
        CheckConstraint("max_retries >= 0", name="positive_max_retries"),
        CheckConstraint("current_retries >= 0", name="positive_current_retries"),
        CheckConstraint("current_retries <= max_retries", name="valid_retry_count"),
        CheckConstraint("timeout_seconds > 0", name="positive_timeout"),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NOT NULL",
            name="valid_completion_time",
        ),
        CheckConstraint(
            "started_at IS NULL OR scheduled_at IS NULL OR started_at >= scheduled_at",
            name="valid_start_time",
        ),
    )


class TaskExecution(Base):

    __tablename__ = "task_executions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    task_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    node_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    execution_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        String(20), default=TaskStatus.QUEUED, nullable=False, index=True
    )

    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storage_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    network_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    execution_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    queue_wait_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    worker_hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="executions")
    node: Mapped[Optional["Node"]] = relationship("Node")

    __table_args__ = (
        Index("idx_execution_task_number", "task_id", "execution_number"),
        Index("idx_execution_status_queued", "status", "queued_at"),
        Index("idx_execution_node_status", "node_id", "status"),
        Index("idx_execution_timing", "started_at", "completed_at"),
        CheckConstraint("execution_number > 0", name="positive_execution_number"),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NOT NULL",
            name="valid_execution_completion",
        ),
        CheckConstraint(
            "started_at IS NULL OR started_at >= queued_at",
            name="valid_execution_start",
        ),
        CheckConstraint(
            "cpu_usage_percent IS NULL OR (cpu_usage_percent >= 0 AND cpu_usage_percent <= 100)",
            name="valid_cpu_usage",
        ),
    )


class TaskResource(Base):

    __tablename__ = "task_resources"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    task_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cpu_cores_required: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )
    memory_gb_required: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False
    )
    storage_gb_required: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )
    gpu_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gpu_memory_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    bandwidth_mbps_required: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    network_latency_max_ms: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    preferred_regions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    excluded_regions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    required_node_capabilities: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True
    )

    allocated_node_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    allocated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    special_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    container_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    environment_requirements: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task: Mapped["Task"] = relationship("Task", back_populates="resource_requirements")
    allocated_node: Mapped[Optional["Node"]] = relationship("Node")

    __table_args__ = (
        Index("idx_resource_task", "task_id"),
        Index("idx_resource_allocated_node", "allocated_node_id"),
        Index("idx_resource_allocation_time", "allocated_at", "released_at"),
        CheckConstraint("cpu_cores_required > 0", name="positive_cpu_requirement"),
        CheckConstraint("memory_gb_required > 0", name="positive_memory_requirement"),
        CheckConstraint("storage_gb_required > 0", name="positive_storage_requirement"),
        CheckConstraint(
            "gpu_memory_gb IS NULL OR gpu_memory_gb > 0", name="positive_gpu_memory"
        ),
        CheckConstraint(
            "bandwidth_mbps_required IS NULL OR bandwidth_mbps_required > 0",
            name="positive_bandwidth",
        ),
        CheckConstraint(
            "network_latency_max_ms IS NULL OR network_latency_max_ms > 0",
            name="positive_latency",
        ),
        CheckConstraint(
            "released_at IS NULL OR allocated_at IS NOT NULL", name="valid_release_time"
        ),
        CheckConstraint(
            "released_at IS NULL OR allocated_at IS NULL OR released_at >= allocated_at",
            name="valid_allocation_period",
        ),
    )


class TaskSchedule(Base):

    __tablename__ = "task_schedules"

    # Primary key (one-to-one with task)
    task_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    schedule_type: Mapped[ScheduleType] = mapped_column(
        String(20), default=ScheduleType.ONE_TIME, nullable=False
    )

    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    interval_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_runs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    skip_missed_runs: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    max_missed_runs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_schedule_next_run", "next_run_at", "is_active"),
        Index("idx_schedule_type", "schedule_type"),
        CheckConstraint(
            "schedule_type != 'cron' OR cron_expression IS NOT NULL",
            name="cron_expression_required",
        ),
        CheckConstraint(
            "schedule_type != 'interval' OR interval_seconds IS NOT NULL",
            name="interval_required",
        ),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="valid_schedule_period",
        ),
        CheckConstraint(
            "interval_seconds IS NULL OR interval_seconds > 0", name="positive_interval"
        ),
        CheckConstraint("total_runs >= 0", name="positive_total_runs"),
        CheckConstraint("max_runs IS NULL OR max_runs > 0", name="positive_max_runs"),
        CheckConstraint(
            "max_missed_runs IS NULL OR max_missed_runs >= 0",
            name="positive_max_missed",
        ),
    )
