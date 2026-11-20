import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
base_dir = Path(__file__).resolve().parent.parent.parent
env_path = base_dir / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback to .env.example if .env not yet created
    example_path = base_dir / ".env.example"
    if example_path.exists():
        load_dotenv(dotenv_path=example_path)


def get_clean_env(key: str, default: str = "") -> str:
    """Retrieve environment variable cleanly, stripping whitespace and quotes."""
    val = os.getenv(key)
    if val is None:
        val = os.getenv(key.upper())
    if val is None:
        val = os.getenv(key.lower())
    if val is None:
        for k, v in os.environ.items():
            if k.strip().lower() == key.strip().lower():
                val = v
                break
    if val is None:
        val = default
    if isinstance(val, str):
        return val.strip().strip("\"'")
    return val


class Settings:
    PROJECT_NAME: str = "Viniyog ONE - Financial Coach"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = get_clean_env("ENVIRONMENT", "development")
    LOG_LEVEL: str = get_clean_env("LOG_LEVEL", "INFO")

    # Google Cloud Vertex AI Settings (Application Default Credentials - ADC)
    LLM_PROVIDER: str = "vertexai"
    GOOGLE_CLOUD_PROJECT: str = get_clean_env("GOOGLE_CLOUD_PROJECT", "lakshos")
    GOOGLE_VERTEX_LOCATION: str = get_clean_env("GOOGLE_VERTEX_LOCATION", get_clean_env("GOOGLE_CLOUD_REGION", "global"))
    GOOGLE_CLOUD_REGION: str = GOOGLE_VERTEX_LOCATION

    # Models: Flash for normal tasks, Pro Preview for reasoning tasks
    GOOGLE_NORMAL_MODEL: str = get_clean_env("GOOGLE_NORMAL_MODEL", "gemini-2.5-flash")
    GOOGLE_REASONING_MODEL: str = get_clean_env("GOOGLE_REASONING_MODEL", "gemini-3.1-pro-preview")

    # Database Settings
    MONGO_SIMULATION: bool = get_clean_env("MONGO_SIMULATION", "true").lower() in ("true", "1", "yes")
    MONGO_URI: str = get_clean_env("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = get_clean_env("MONGO_DB_NAME", "viniyogone_db")

    # Web Search Tooling
    TAVILY_API_KEY: str = get_clean_env("TAVILY_API_KEY", "")

    # LangSmith Tracing & Observability
    LANGSMITH_TRACING: bool = get_clean_env("LANGSMITH_TRACING", "false").lower() in ("true", "1", "yes")
    LANGSMITH_ENDPOINT: str = get_clean_env("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    LANGSMITH_API_KEY: str = get_clean_env("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = get_clean_env("LANGSMITH_PROJECT", "Google-Buildathon-VO")


settings = Settings()

# # Automatically configure LangSmith / LangChain tracing environment variables
# if settings.LANGSMITH_TRACING:
#     os.environ["LANGSMITH_TRACING"] = "true"
#     os.environ["LANGCHAIN_TRACING_V2"] = "true"
#     if settings.LANGSMITH_API_KEY:
#         os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
#         os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
#     if settings.LANGSMITH_PROJECT:
#         os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
#         os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
#     if settings.LANGSMITH_ENDPOINT:
#         os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
#         os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
