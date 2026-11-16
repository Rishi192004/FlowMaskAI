"""Create dataset, raw_events, cleaned_events, etl_executions, and data_quality_issues tables

Revision ID: 0002_create_etl_tables
Revises: 0001_initial
Create Date: 2026-11-16 01:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_create_etl_tables"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    uuid_type = postgresql.UUID(as_uuid=True) if is_pg else sa.CHAR(36)

    # 1. datasets
    op.create_table(
        "datasets",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("delimiter", sa.String(10), nullable=False, server_default=","),
        sa.Column("status", sa.String(50), nullable=False, server_default="uploaded"),
        sa.Column("total_rows_raw", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("column_mapping", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()" if is_pg else "CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()" if is_pg else "CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # 2. raw_events
    op.create_table(
        "raw_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "dataset_id",
            uuid_type,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()" if is_pg else "CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_raw_events_dataset_id", "raw_events", ["dataset_id"])

    # 3. cleaned_events
    op.create_table(
        "cleaned_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "dataset_id",
            uuid_type,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "raw_event_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("case_id", sa.String(255), nullable=False),
        sa.Column("activity", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource", sa.String(255), nullable=True),
        sa.Column("extra_attributes", sa.JSON(), nullable=True),
        sa.Column("is_out_of_order", sa.Boolean(), nullable=False, server_default=sa.text("false" if is_pg else "0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()" if is_pg else "CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_cleaned_events_dataset_id", "cleaned_events", ["dataset_id"])
    op.create_index("ix_cleaned_events_case_id", "cleaned_events", ["case_id"])
    op.create_index("ix_cleaned_events_activity", "cleaned_events", ["activity"])
    op.create_index("ix_cleaned_events_timestamp", "cleaned_events", ["timestamp"])

    # 4. etl_executions
    op.create_table(
        "etl_executions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column(
            "dataset_id",
            uuid_type,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("total_records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_value_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_loaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_etl_executions_dataset_id", "etl_executions", ["dataset_id"])

    # 5. data_quality_issues
    op.create_table(
        "data_quality_issues",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "dataset_id",
            uuid_type,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "etl_execution_id",
            uuid_type,
            sa.ForeignKey("etl_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("issue_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("is_fatal", sa.Boolean(), nullable=False, server_default=sa.text("false" if is_pg else "0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()" if is_pg else "CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_data_quality_issues_dataset_id", "data_quality_issues", ["dataset_id"])
    op.create_index("ix_data_quality_issues_etl_execution_id", "data_quality_issues", ["etl_execution_id"])
    op.create_index("ix_data_quality_issues_issue_type", "data_quality_issues", ["issue_type"])


def downgrade() -> None:
    op.drop_table("data_quality_issues")
    op.drop_table("etl_executions")
    op.drop_table("cleaned_events")
    op.drop_table("raw_events")
    op.drop_table("datasets")
