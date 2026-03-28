"""Configuration settings for Exercise Competition.

Settings are loaded from environment variables with the prefix 'EXERCISE_COMPETITION_'.
Pydantic-settings handles the parsing and validation.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the application, loaded from environment variables.

    Attributes:
        log_level: The logging level for the application.
        json_logs: Flag to enable or disable JSON formatted logs.
        include_timestamp: Flag to include timestamps in logs.
        database_url: SQLAlchemy database URL.
        rate_limit_rpm: Rate limit requests per minute.
        week_min: First competition week number.
        week_max: Last competition week number (total weeks).
        compliance_threshold: Minimum exercise days per week for a point.
        csrf_ttl_seconds: CSRF token time-to-live in seconds.
    """

    model_config = SettingsConfigDict(
        env_prefix="exercise_competition_",
        case_sensitive=False,
        extra="ignore",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = False
    include_timestamp: bool = True

    # Database
    database_url: str = "sqlite:///data/competition.db"

    # Rate limiting
    rate_limit_rpm: int = 60

    # Competition rules
    week_min: int = 1
    week_max: int = 20
    compliance_threshold: int = 2

    # Security
    csrf_ttl_seconds: int = 1800  # 30 minutes


# A single, global instance of the settings
settings = Settings()
