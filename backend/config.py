"""
Configuration management using simple class.
Loads environment variables and provides a singleton settings instance.
"""
import os
from typing import Optional

from dotenv import load_dotenv

# .env 파일을 자동으로 로드하여 os.getenv()에서 사용할 수 있도록 함
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # FAISS configuration
        self.faiss_index_path = os.getenv("FAISS_INDEX_PATH", "./data/faiss/index.faiss")
        self.faiss_meta_path = os.getenv("FAISS_META_PATH", "./data/faiss/meta.jsonl")
        self.faiss_top_k = int(os.getenv("FAISS_TOP_K", "5"))
        
        # API endpoints (placeholders)
        # CALENDAR_ENDPOINT 하나만 세팅하면 날씨/공휴일 모두 이 엔드포인트를 사용합니다.
        # (원하면 KMA_ENDPOINT, HOLIDAY_ENDPOINT를 따로 쓸 수도 있습니다.)
        self.calendar_endpoint = os.getenv("CALENDAR_ENDPOINT")
        self.kma_endpoint = os.getenv("KMA_ENDPOINT", "<KMA_ENDPOINT>")
        self.kma_api_key = os.getenv("KMA_API_KEY")
        self.holiday_endpoint = os.getenv("HOLIDAY_ENDPOINT", "<HOLIDAY_ENDPOINT>")
        self.holiday_api_key = os.getenv("HOLIDAY_API_KEY")
        
        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.use_openai_embeddings = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"
        
        # LLM configuration (Global defaults)
        self.llm_model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")  # gpt-4o-mini, gpt-4, gpt-3.5-turbo
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
        
        # Agent-specific LLM models (optional overrides)
        self.supervisor_model = os.getenv("SUPERVISOR_MODEL", self.llm_model)
        self.law_rag_model = os.getenv("LAW_RAG_MODEL", self.llm_model)
        self.cpm_model = os.getenv("CPM_MODEL", self.llm_model)
        self.merger_model = os.getenv("MERGER_MODEL", self.llm_model)
        
        # Agent-specific temperatures (optional overrides)
        self.supervisor_temperature = float(os.getenv("SUPERVISOR_TEMPERATURE", str(self.llm_temperature)))
        self.law_rag_temperature = float(os.getenv("LAW_RAG_TEMPERATURE", str(self.llm_temperature)))
        self.cpm_temperature = float(os.getenv("CPM_TEMPERATURE", str(self.llm_temperature)))
        self.merger_temperature = float(os.getenv("MERGER_TEMPERATURE", str(self.llm_temperature)))
        
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