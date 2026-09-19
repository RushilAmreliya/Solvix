"""
NowCast Fusion — Application Settings

Centralises all configuration in one place.
Values are loaded from environment variables (or a .env file if present).

Usage:
    from backend.settings import settings
    print(settings.MODEL_PATH)
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    Copy .env.example → .env and fill in values to override defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.
    # Default is open ("*") for demo; restrict in production.
    CORS_ORIGINS: str = "*"

    # ── Data Paths ────────────────────────────────────────────────────────────
    DATA_DIR: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data")
    )

    # ── Model ─────────────────────────────────────────────────────────────────
    MODEL_PATH: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "engine/nowcast_model.pth")
    )

    # ── Nowcasting ────────────────────────────────────────────────────────────
    SEQ_IN:     int   = 3    # Input frames  (3 × 30 min = 1.5 hrs)
    MAX_BUFFER: int   = 20   # Max frames held in memory
    CNN_BLEND:  float = 0.30 # CNN contribution in blended forecast (0 = PySTEPS-only)

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS_ORIGINS as a Python list."""
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def data_4km_path(self) -> str:
        return os.path.join(self.DATA_DIR, "assam_persiann_4km.npy")

    @property
    def data_10km_path(self) -> str:
        return os.path.join(self.DATA_DIR, "assam_gpm_sample.npy")


# Singleton — import this everywhere instead of hardcoding values
settings = Settings()
