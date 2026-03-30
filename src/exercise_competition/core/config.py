"""Configuration settings for Exercise Competition.

Settings are loaded from environment variables with the prefix 'EXERCISE_COMPETITION_'.
Pydantic-settings handles the parsing and validation.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator
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
    rate_limit_rpm: Annotated[int, Field(ge=1)] = 60

    # Competition rules
    week_min: Annotated[int, Field(ge=1)] = 1
    week_max: Annotated[int, Field(ge=1)] = 20
    compliance_threshold: Annotated[int, Field(ge=1, le=7)] = 2

    # Security
    csrf_ttl_seconds: Annotated[int, Field(ge=60)] = 1800  # 30 minutes

    @model_validator(mode="after")
    def _validate_week_range(self) -> Settings:
        """Ensure week_min <= week_max."""
        if self.week_min > self.week_max:
            msg = f"week_min ({self.week_min}) must be <= week_max ({self.week_max})"
            raise ValueError(msg)
        return self

    # Strava integration
    strava_client_id: str = ""
    strava_client_secret: str = ""  # NOSONAR(S2068) loaded from env vars, empty default
    strava_redirect_uri: str = ""
    strava_webhook_verify_token: str = (
        ""  # NOSONAR(S2068) loaded from env vars, empty default
    )
    strava_min_activity_minutes: Annotated[int, Field(ge=1, le=1440)] = 30


# A single, global instance of the settings
settings = Settings()
