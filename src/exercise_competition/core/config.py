"""Configuration settings for Exercise Competition.

Settings are loaded from environment variables with the prefix 'EXERCISE_COMPETITION_'.
Pydantic-settings handles the parsing and validation.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration settings for the application, loaded from environment variables.

    Attributes:
        log_level: The logging level for the application.
        json_logs: Flag to enable or disable JSON formatted logs.
        include_timestamp: Flag to include timestamps in logs.
    """

    model_config = SettingsConfigDict(
        env_prefix="exercise_competition_",
        case_sensitive=False,
        extra="ignore",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = False
    include_timestamp: bool = True
    database_url: str = "sqlite:///data/competition.db"
    rate_limit_rpm: int = 60


# A single, global instance of the settings
settings = Settings()
