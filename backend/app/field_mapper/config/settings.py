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

    # Matching configuration - Two-Tier Confidence System
    high_confidence_threshold: float = 0.7  # Auto-confirm mappings
    medium_confidence_threshold: float = 0.4  # Suggest for review
    confidence_threshold: float = 0.4  # Minimum to show (legacy compatibility)
    max_suggestions: int = 10  # Increased from 5 to store more alternatives
    sample_size: int = 1000  # Max rows to sample for profiling

    # Strategy weights (tuned based on validation results 2025-10-11)
    # Individual strategy accuracy: Contextual(66%), DataType(55%), Exact(44%), Label(33%), Fuzzy(33%), Pattern(22%), Selection(0%), Statistical(0%)
    exact_match_weight: float = 0.8      # 44% accuracy, 80% precision - Keep moderate
    label_match_weight: float = 0.3      # 33% accuracy, 100% precision - Low weight but keep for high precision
    selection_value_weight: float = 0.0  # 0% accuracy - DISABLED
    data_type_weight: float = 0.3        # 55% accuracy, 62% precision - Low weight, needs semantic fix
    pattern_match_weight: float = 0.0    # 22% accuracy - DISABLED
    statistical_weight: float = 0.0      # 0% accuracy - DISABLED
    contextual_weight: float = 1.0       # 66% accuracy, 75% precision - BEST PERFORMER
    fuzzy_match_weight: float = 0.0      # 33% accuracy - DISABLED

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
