from pathlib import Path
from core.config.model import BASE_CONFIG
PROJECT_ROOT = Path(__file__).resolve().parent


CONFIG = {
    "test": BASE_CONFIG,
    "curator": BASE_CONFIG,
    "suggestor": BASE_CONFIG,
    "diagnostician": BASE_CONFIG
}
