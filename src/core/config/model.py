from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
from dotenv import load_dotenv
import os
load_dotenv() 
BASE_URL = os.getenv("BASE_URL")


MODEL_PROVIDER = "vllm"


COMMON_MODEL_CONFIG = {
    "api": {
        "type": "api",
        "model_name": "gpt-5-mini",
        "temperature": 0,
    },
    "vllm": {
        "type": "vllm",
        "model_name": "Qwen/Qwen3.6-27B-FP8",
        "base_url": "http://vllm_service:8000/v1",
        "api_key": "token-not-needed",
        "temperature": 0,
    },
    "ollama": {
        "type": "ollama",
        "model_name": "gemma4:31b",
        "temperature": 0,
        "base_url": f"{BASE_URL}:11434",
    }
}


BASE_CONFIG = COMMON_MODEL_CONFIG[MODEL_PROVIDER]