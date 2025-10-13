"""
LLM Client wrapper for OpenAI API.
Provides unified interface for LLM calls across all agents.
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI
from ..config import get_settings


class LLMClient:
    """Unified LLM client for all agents."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client."""
        if self.settings.openai_api_key:
            self.client = OpenAI(api_key=self.settings.openai_api_key)
        else:
            print("Warning: OpenAI API key not set. LLM features will be disabled.")
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Call OpenAI chat completion API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            model: Model to use (overrides config)
            
        Returns:
            Generated text response
        """
        if not self.client:
            return self._fallback_response(messages)
        
        try:
            response = self.client.chat.completions.create(
                model=model or self.settings.llm_model,
                messages=messages,
                temperature=temperature or self.settings.llm_temperature,
                max_tokens=max_tokens or self.settings.llm_max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"LLM API error: {e}")
            return self._fallback_response(messages)
    
    def _fallback_response(self, messages: List[Dict[str, str]]) -> str:
        """Fallback response when LLM is unavailable."""
        return "LLM이 설정되지 않았거나 오류가 발생했습니다. OpenAI API 키를 확인해주세요."
    
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.client is not None


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

