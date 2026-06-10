"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the observatory platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OBSERVATORY_",
        extra="ignore",
    )

    env: Literal["local", "test", "prod"] = "local"
    warehouse_path: Path = Field(default=Path("data/warehouse/observatory.duckdb"))
    raw_log_dir: Path = Field(default=Path("data/raw/agent_runs"))
    parquet_dir: Path = Field(default=Path("data/processed/parquet"))
    metadata_dir: Path = Field(default=Path("data/metadata"))
    quarantine_dir: Path = Field(default=Path("data/quarantine"))

    use_llm: bool = False
    llm_provider: str = "ollama"
    llm_model: str = "llama3"
    api_host: str = "localhost"
    api_port: int = 8000

    latency_threshold_ms: int = 5000
    latency_good_ms: int = 2000
    cost_threshold_usd: float = 0.005
    cost_good_usd: float = 0.001
    reliability_alert_threshold: float = 0.70
    classification_confidence_threshold: float = 0.60
    retrieval_relevance_threshold: float = 0.5
    format_score_threshold: float = 0.5
    tool_score_threshold: float = 0.5
    correctness_failure_threshold: float = 0.4

    default_run_count: int = 10_000
    default_seed: int = 42

    # SQL evaluator allowed schema
    allowed_sql_tables: set[str] = Field(
        default_factory=lambda: {"orders", "customers", "products", "revenue_daily"}
    )
    allowed_sql_columns: dict[str, set[str]] = Field(
        default_factory=lambda: {
            "orders": {"order_id", "customer_id", "amount", "order_date"},
            "customers": {"customer_id", "name", "segment"},
            "products": {"product_id", "name", "category"},
            "revenue_daily": {"date", "revenue", "region"},
        }
    )
    destructive_sql_keywords: set[str] = Field(
        default_factory=lambda: {
            "drop", "delete", "truncate", "alter", "insert", "update", "create",
        }
    )

    def project_root(self) -> Path:
        """Return project root (parent of observatory package)."""
        return Path(__file__).resolve().parents[2]

    def resolve_path(self, path: Path) -> Path:
        """Resolve relative paths against project root."""
        if path.is_absolute():
            return path
        return self.project_root() / path

    def ensure_directories(self) -> None:
        """Create required data directories."""
        for directory in (
            self.raw_log_dir,
            self.parquet_dir,
            self.metadata_dir,
            self.quarantine_dir,
            self.warehouse_path.parent,
        ):
            resolved = self.resolve_path(directory)
            resolved.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
