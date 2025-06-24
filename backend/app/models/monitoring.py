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
    from .task import Task
    from .user import User


class MetricType(str, Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    CUSTOM = "custom"
    PERFORMANCE = "performance"
    SECURITY = "security"


class MetricUnit(str, Enum):
    PERCENTAGE = "percentage"
    BYTES = "bytes"
    KILOBYTES = "kilobytes"
    MEGABYTES = "megabytes"
    GIGABYTES = "gigabytes"
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    COUNT = "count"
    RATE_PER_SECOND = "rate_per_second"
    BOOLEAN = "boolean"
    STRING = "string"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MonitoringTarget(str, Enum):
    NODE = "node"
    TASK = "task"
    APPLICATION = "application"
    SYSTEM = "system"
    USER = "user"
    DEPLOYMENT = "deployment"


class Metric(Base):

    __tablename__ = "metrics"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metric_type: Mapped[MetricType] = mapped_column(
        String(20), nullable=False, index=True
    )
    unit: Mapped[MetricUnit] = mapped_column(String(20), nullable=False)

    # Metric source and target
    source_type: Mapped[MonitoringTarget] = mapped_column(
        String(20), nullable=False, index=True
    )
    source_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), nullable=True, index=True
    )

    # Metric value and metadata
    value: Mapped[float] = mapped_column(Float, nullable=False)
    string_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    labels: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    collected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Collection metadata
    collection_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    collector_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Data quality
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Retention and archival
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="metric", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_metric_name_timestamp", "name", "timestamp"),
        Index("idx_metric_source", "source_type", "source_id"),
        Index("idx_metric_type_timestamp", "metric_type", "timestamp"),
        Index("idx_metric_retention", "retention_days", "archived"),
        Index("idx_metric_tags", "tags", postgresql_using="gin"),
        CheckConstraint("retention_days > 0", name="positive_retention"),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="valid_confidence",
        ),
    )


class HealthCheck(Base):

    __tablename__ = "health_checks"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    check_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Target being monitored
    target_type: Mapped[MonitoringTarget] = mapped_column(
        String(20), nullable=False, index=True
    )
    target_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), nullable=True, index=True
    )

    # Health status
    status: Mapped[HealthStatus] = mapped_column(
        String(20), default=HealthStatus.UNKNOWN, nullable=False, index=True
    )
    previous_status: Mapped[Optional[HealthStatus]] = mapped_column(
        String(20), nullable=True
    )

    # Check configuration
    endpoint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Check results
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    last_check_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    next_check_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    status_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Statistics
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    total_checks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uptime_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Configuration
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_on_failure: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    __table_args__ = (
        Index("idx_health_target", "target_type", "target_id"),
        Index("idx_health_status_check", "status", "last_check_at"),
        Index("idx_health_next_check", "next_check_at", "enabled"),
        Index("idx_health_name_type", "name", "check_type"),
        CheckConstraint("timeout_seconds > 0", name="positive_timeout"),
        CheckConstraint("interval_seconds > 0", name="positive_interval"),
        CheckConstraint("retries >= 0", name="non_negative_retries"),
        CheckConstraint(
            "consecutive_failures >= 0", name="non_negative_consecutive_failures"
        ),
        CheckConstraint("total_checks >= 0", name="non_negative_total_checks"),
        CheckConstraint("total_failures >= 0", name="non_negative_total_failures"),
        CheckConstraint("total_failures <= total_checks", name="valid_failure_count"),
        CheckConstraint(
            "uptime_percentage IS NULL OR (uptime_percentage >= 0 AND uptime_percentage <= 100)",
            name="valid_uptime",
        ),
    )


class Alert(Base):

    __tablename__ = "alerts"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        String(20), nullable=False, index=True
    )
    status: Mapped[AlertStatus] = mapped_column(
        String(20), default=AlertStatus.ACTIVE, nullable=False, index=True
    )

    # Alert source
    source_type: Mapped[MonitoringTarget] = mapped_column(
        String(20), nullable=False, index=True
    )
    source_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), nullable=True, index=True
    )

    # Related entities
    metric_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("metrics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Alert conditions
    condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    threshold_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Alert timing
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Alert handling
    acknowledged_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notification tracking
    notification_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notification_channels: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True
    )
    escalation_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Alert metadata
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    additional_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    metric: Mapped[Optional["Metric"]] = relationship("Metric", back_populates="alerts")
    rule: Mapped[Optional["AlertRule"]] = relationship(
        "AlertRule", back_populates="alerts"
    )
    acknowledged_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[acknowledged_by]
    )
    resolved_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[resolved_by]
    )

    __table_args__ = (
        Index("idx_alert_severity_status", "severity", "status"),
        Index("idx_alert_source", "source_type", "source_id"),
        Index("idx_alert_triggered", "triggered_at", "status"),
        Index("idx_alert_escalation", "escalation_level", "status"),
        CheckConstraint("escalation_level >= 0", name="non_negative_escalation"),
        CheckConstraint(
            "acknowledged_at IS NULL OR acknowledged_at >= triggered_at",
            name="valid_acknowledge_time",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= triggered_at",
            name="valid_resolve_time",
        ),
    )


class AlertRule(Base):

    __tablename__ = "alert_rules"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rule targeting
    target_type: Mapped[MonitoringTarget] = mapped_column(
        String(20), nullable=False, index=True
    )
    target_filter: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Rule conditions
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    condition_operator: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # >, <, >=, <=, ==, !=
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    evaluation_window_seconds: Mapped[int] = mapped_column(
        Integer, default=300, nullable=False
    )

    # Alert configuration
    severity: Mapped[AlertSeverity] = mapped_column(String(20), nullable=False)
    alert_title_template: Mapped[str] = mapped_column(String(255), nullable=False)
    alert_description_template: Mapped[str] = mapped_column(Text, nullable=False)

    # Rule behavior
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_alerts_per_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Notification configuration
    notification_channels: Mapped[Optional[List[str]]] = mapped_column(
        JSON, nullable=True
    )
    escalation_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Rule statistics
    total_evaluations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_alerts_generated: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    last_evaluation_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_alert_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="rule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_rule_target_metric", "target_type", "metric_name"),
        Index("idx_rule_enabled_evaluation", "enabled", "last_evaluation_at"),
        Index("idx_rule_name", "name"),
        CheckConstraint(
            "evaluation_window_seconds > 0", name="positive_evaluation_window"
        ),
        CheckConstraint("cooldown_seconds >= 0", name="non_negative_cooldown"),
        CheckConstraint(
            "max_alerts_per_hour IS NULL OR max_alerts_per_hour > 0",
            name="positive_max_alerts",
        ),
        CheckConstraint("total_evaluations >= 0", name="non_negative_evaluations"),
        CheckConstraint(
            "total_alerts_generated >= 0", name="non_negative_alerts_generated"
        ),
        CheckConstraint(
            "total_alerts_generated <= total_evaluations", name="valid_alert_count"
        ),
    )


class PerformanceProfile(Base):

    __tablename__ = "performance_profiles"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Profile target
    target_type: Mapped[MonitoringTarget] = mapped_column(
        String(20), nullable=False, index=True
    )
    target_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), nullable=True, index=True
    )

    # Profiling period
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    # Performance metrics
    cpu_avg_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_max_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_avg_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_max_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # I/O metrics
    disk_read_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_write_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    network_in_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    network_out_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Response time metrics
    avg_response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p95_response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p99_response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Throughput metrics
    requests_per_second: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    errors_per_second: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_rate_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Performance score
    performance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bottlenecks: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Detailed analysis
    detailed_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    analysis_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Profile metadata
    profile_type: Mapped[str] = mapped_column(String(50), nullable=False)
    automated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_profile_target", "target_type", "target_id"),
        Index("idx_profile_time_range", "start_time", "end_time"),
        Index("idx_profile_score", "performance_score"),
        Index("idx_profile_type", "profile_type"),
        CheckConstraint("end_time > start_time", name="valid_time_range"),
        CheckConstraint("duration_seconds > 0", name="positive_duration"),
        CheckConstraint(
            "cpu_avg_percent IS NULL OR (cpu_avg_percent >= 0 AND cpu_avg_percent <= 100)",
            name="valid_cpu_avg",
        ),
        CheckConstraint(
            "cpu_max_percent IS NULL OR (cpu_max_percent >= 0 AND cpu_max_percent <= 100)",
            name="valid_cpu_max",
        ),
        CheckConstraint(
            "error_rate_percent IS NULL OR (error_rate_percent >= 0 AND error_rate_percent <= 100)",
            name="valid_error_rate",
        ),
        CheckConstraint(
            "performance_score IS NULL OR (performance_score >= 0 AND performance_score <= 100)",
            name="valid_performance_score",
        ),
    )


class SystemEvent(Base):

    __tablename__ = "system_events"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )

    # Event identification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Event source
    source_type: Mapped[MonitoringTarget] = mapped_column(
        String(20), nullable=False, index=True
    )
    source_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), nullable=True, index=True
    )

    # Event context
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Event data
    event_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    before_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Event outcome
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Event timing
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Event classification
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    user: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        Index("idx_event_type_timestamp", "event_type", "timestamp"),
        Index("idx_event_source", "source_type", "source_id"),
        Index("idx_event_user_timestamp", "user_id", "timestamp"),
        Index("idx_event_success_timestamp", "success", "timestamp"),
        Index("idx_event_category_severity", "category", "severity"),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0", name="non_negative_duration"
        ),
    )
