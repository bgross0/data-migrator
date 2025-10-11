"""
Configuration settings for the deterministic field mapper system.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class FieldMapperSettings(BaseSettings):
    """Configuration settings for the field mapper system."""

    # Paths
    odoo_dictionary_path: str = os.getenv(
        "ODOO_DICTIONARY_PATH",
        str(Path(__file__).parent.parent.parent.parent.parent / "odoo-dictionary")
    )

    # Caching
    cache_enabled: bool = True
    cache_size: int = 10000
    cache_ttl_seconds: int = 3600  # 1 hour

    # Performance
    max_workers: int = 4
    timeout_seconds: float = 60.0
    match_timeout_ms: float = 1000.0  # 1 second per column

    # Matching configuration
    confidence_threshold: float = 0.6
    high_confidence_threshold: float = 0.8
    max_suggestions: int = 5
    sample_size: int = 1000  # Max rows to sample for profiling

    # Strategy weights
    exact_match_weight: float = 1.0
    label_match_weight: float = 0.95
    selection_value_weight: float = 0.9
    data_type_weight: float = 0.7
    pattern_match_weight: float = 0.75
    statistical_weight: float = 0.6
    contextual_weight: float = 0.8
    fuzzy_match_weight: float = 0.65

    # Database
    history_db_path: str = os.getenv(
        "FIELD_MAPPER_HISTORY_DB",
        str(Path(__file__).parent.parent.parent.parent / "data" / "mapping_history.db")
    )

    # Logging
    log_level: str = os.getenv("FIELD_MAPPER_LOG_LEVEL", "INFO")

    # Performance monitoring
    enable_performance_monitoring: bool = True
    performance_alert_threshold_ms: float = 100.0

    # Rate limiting
    enable_rate_limiting: bool = True
    rate_limit_calls: int = 1000
    rate_limit_period: int = 60  # seconds

    class Config:
        env_prefix = "FIELD_MAPPER_"
        case_sensitive = False


# Global settings instance
settings = FieldMapperSettings()
