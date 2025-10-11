"""
Configuration management using simple class.
Loads environment variables and provides a singleton settings instance.
"""
import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # FAISS configuration
        self.faiss_index_path = os.getenv("FAISS_INDEX_PATH", "./data/faiss/index.faiss")
        self.faiss_meta_path = os.getenv("FAISS_META_PATH", "./data/faiss/meta.jsonl")
        self.faiss_top_k = int(os.getenv("FAISS_TOP_K", "5"))
        
        # API endpoints (placeholders)
        self.kma_endpoint = os.getenv("KMA_ENDPOINT", "<KMA_ENDPOINT>")
        self.kma_api_key = os.getenv("KMA_API_KEY")
        self.holiday_endpoint = os.getenv("HOLIDAY_ENDPOINT", "<HOLIDAY_ENDPOINT>")
        self.holiday_api_key = os.getenv("HOLIDAY_API_KEY")
        
        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.use_openai_embeddings = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"
        
        # Contract defaults
        self.currency = os.getenv("CURRENCY", "KRW")
        
        # Development settings
        self.use_stub = os.getenv("USE_STUB", "true").lower() == "true"


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def format_currency(amount: float, currency: str = "KRW") -> str:
    """Format currency amount for display."""
    if currency == "KRW":
        return f"₩{amount:,.0f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"