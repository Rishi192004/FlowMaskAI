"""
SQLAlchemy ORM models for Datasets, Events (Raw & Cleaned),
ETL Executions, and Data Quality Issues.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.guid import GUID


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    delimiter: Mapped[str] = mapped_column(String(10), default=",", nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="uploaded", nullable=False
    )  # "uploaded", "processing", "processed", "failed"
    total_rows_raw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_mapping: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    raw_events = relationship(
        "RawEvent", back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )
    cleaned_events = relationship(
        "CleanedEvent", back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )
    etl_executions = relationship(
        "ETLExecution", back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )
    quality_issues = relationship(
        "DataQualityIssue", back_populates="dataset", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} name={self.name!r} status={self.status!r}>"


class RawEvent(Base):
    """
    Stores exact unedited original row records as extracted from the input CSV
    to ensure full auditability.
    """
    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    dataset = relationship("Dataset", back_populates="raw_events")

    def __repr__(self) -> str:
        return f"<RawEvent id={self.id} dataset_id={self.dataset_id} row={self.row_index}>"


class CleanedEvent(Base):
    """
    Stores normalized, validated, and typed event log records ready for process mining.
    """
    __tablename__ = "cleaned_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_event_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("raw_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    case_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    activity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    resource: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra_attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_out_of_order: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    dataset = relationship("Dataset", back_populates="cleaned_events")

    def __repr__(self) -> str:
        return f"<CleanedEvent id={self.id} case_id={self.case_id!r} activity={self.activity!r}>"


class ETLExecution(Base):
    """
    Audit trail recording each execution of the ETL transformation and loading cycle.
    Tracks all required metrics: received, valid, duplicates, missing values, rejected, loaded.
    """
    __tablename__ = "etl_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # "running", "completed", "failed"
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Required quality metrics
    total_records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_value_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_loaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    dataset = relationship("Dataset", back_populates="etl_executions")
    quality_issues = relationship(
        "DataQualityIssue", back_populates="execution", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<ETLExecution id={self.id} dataset_id={self.dataset_id} status={self.status!r}>"


class DataQualityIssue(Base):
    """
    Detailed log of every data quality issue identified during ETL processing.
    """
    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    etl_execution_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("etl_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # "MISSING_REQUIRED_FIELD", "INVALID_TIMESTAMP", "DUPLICATE_EVENT", "OUT_OF_ORDER_EVENT", "MALFORMED_ROW"
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "ERROR", "WARNING", "INFO"
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_fatal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    dataset = relationship("Dataset", back_populates="quality_issues")
    execution = relationship("ETLExecution", back_populates="quality_issues")

    def __repr__(self) -> str:
        return f"<DataQualityIssue id={self.id} type={self.issue_type!r} row={self.row_index}>"
