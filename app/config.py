from typing import Any

from pydantic import BaseSettings

from .constants import Environment


class Config(BaseSettings):
    SITE_DOMAIN: str = "ocr.anap.ro"

    ENVIRONMENT: Environment = Environment.PRODUCTION
    CORS_ORIGINS: list[str] = [
        "http://localhost",
        "http://localhost:8080",
    ]
    CORS_ORIGINS_REGEX: str = "*"
    CORS_HEADERS: list[str] = ["*"]
    APP_VERSION: str = "1"


settings = Config()

app_configs: dict[str, Any] = {"title": "App API"}
if settings.ENVIRONMENT.is_deployed:
    app_configs["root_path"] = f"/v{settings.APP_VERSION}"

if not settings.ENVIRONMENT.is_debug:
    app_configs["openapi_url"] = None  # hide docs
