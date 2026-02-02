"""Configuration for LaTeX service."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration."""

    # Service
    service_name: str = "latex-compiler"

    # LaTeX
    latex_compiler: str = "xelatex"
    latex_timeout: int = 60
    latex_compile_passes: int = 2
    latex_keep_aux_files: bool = False

    # S3
    enable_s3: bool = True
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_secure: bool = True

    # RabbitMQ
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_pass: str = "guest"

    # Queues
    latex_compile_queue: str = "latex_compile"
    latex_progress_queue: str = "latex_progress"
    latex_status_queue: str = "latex_status"

    # Paths
    templates_dir: Path = Path("/app/templates")
    temp_dir: Path = Path("/tmp/latex-compile")

    # Limits
    max_compilations_per_minute: int = 5
    max_versions_per_job: int = 10
    max_tex_file_size_kb: int = 500

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()

# Ensure directories exist
settings.temp_dir.mkdir(parents=True, exist_ok=True)
