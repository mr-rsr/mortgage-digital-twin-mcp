import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase Configuration
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")

    # MCP Server Configuration
    mcp_server_host: str = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    mcp_server_port: int = int(os.getenv("MCP_SERVER_PORT", "8000"))

    # Local SQLite DB Path (used when Supabase is not configured)
    local_db_path: str = os.getenv("LOCAL_DB_PATH", "mortgage_twin.db")

    # AI / Embedding Key (optional)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

settings = Settings()
