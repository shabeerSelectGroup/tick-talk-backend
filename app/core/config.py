import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-in-production"
    app_debug: bool = True
    app_cors_origins: str = "http://localhost:5173"
    app_public_url: str = "http://localhost:5173"

    database_url: str = "mysql+aiomysql://ticktalk:ticktalk@localhost:3306/ticktalk"
    redis_url: str = "redis://localhost:6379/0"

    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # Admin portal: shared security code (set in production)
    admin_security_code: str = ""
    admin_login_email: str = "admin@ticktalk.app"

    session_expire_hours: int = 24

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "ticktalk-selfies"
    r2_public_url: str = ""
    r2_endpoint_url: str = ""

    selfie_max_upload_bytes: int = 8 * 1024 * 1024
    selfie_jpeg_quality: int = 90
    selfie_max_dimension: int = 1920
    selfie_thumbnail_size: int = 480
    local_storage_dir: str = "storage/uploads"
    local_storage_public_base: str = ""
    exports_dir: str = "storage/exports"

    ws_heartbeat_interval_sec: float = 30.0
    ws_heartbeat_timeout_sec: float = 90.0

    # Web Push (VAPID) — generate: npx web-push generate-vapid-keys
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@ticktalk.app"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]


@lru_cache
def _get_settings_cached() -> Settings:
    return Settings()


def get_settings() -> Settings:
    """Reload .env on each call in development so ADMIN_SECURITY_CODE changes apply without restart."""
    env = os.getenv("APP_ENV", "development").lower()
    if env in ("development", "dev", "local"):
        return Settings()
    return _get_settings_cached()
