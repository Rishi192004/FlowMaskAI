"""
FlowMind ETL package: Extraction, Transformation, Validation, and Loading.
"""
from app.etl.detector import detect_columns_and_preview, detect_delimiter, suggest_column_mapping
from app.etl.normalizer import normalize_activity_name, parse_timestamp_to_utc
from app.etl.validator import EventLogValidator, EventValidationResult

__all__ = [
    "detect_delimiter",
    "detect_columns_and_preview",
    "suggest_column_mapping",
    "normalize_activity_name",
    "parse_timestamp_to_utc",
    "EventLogValidator",
    "EventValidationResult",
    "run_etl_pipeline",
]


def run_etl_pipeline(*args, **kwargs):
    from app.etl.pipeline import run_etl_pipeline as _run
    return _run(*args, **kwargs)
