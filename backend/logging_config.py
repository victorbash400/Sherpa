import logging
import os
import warnings


class BenignContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "Failed to detach context" not in record.getMessage()


def configure_logging() -> None:
    warnings.filterwarnings(
        "ignore",
        message=(
            r"\[EXPERIMENTAL\] feature FeatureName\."
            r"(PLUGGABLE_AUTH|_MCP_GRACEFUL_ERROR_HANDLING|"
            r"BASE_AUTHENTICATED_TOOL|JSON_SCHEMA_FOR_FUNC_DECL|"
            r"PROGRESSIVE_SSE_STREAMING) is enabled\."
        ),
        category=UserWarning,
    )
    logging.basicConfig(
        level=os.getenv("SHERPA_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    for name in ("google_adk", "google_genai", "httpx", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("opentelemetry.context").addFilter(BenignContextFilter())


def log_text(value: str, limit: int = 180) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def add_token_usage(totals: dict[str, int], usage: object | None) -> None:
    if usage is None:
        return
    for key, attribute in (
        ("input", "prompt_token_count"),
        ("output", "candidates_token_count"),
        ("thinking", "thoughts_token_count"),
        ("total", "total_token_count"),
    ):
        value = getattr(usage, attribute, None)
        if isinstance(value, int):
            totals[key] += value
