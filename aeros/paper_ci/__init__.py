"""Paper CI utilities for result-born provenance."""
from .adapters import payload_from_statsmodels
from .result_registry import (
    ResultRecord,
    register_payload,
    register_payload_file,
    sync_result_index,
)

__all__ = [
    "ResultRecord",
    "payload_from_statsmodels",
    "register_payload",
    "register_payload_file",
    "sync_result_index",
]
