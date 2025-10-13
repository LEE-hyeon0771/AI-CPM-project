"""
Law/Regulation RAG Agent for KOSHA PDFs search.
Uses local FAISS index for document retrieval with LLM-based interpretation.
"""
from typing import List, Dict, Any, Optional
from ..tools.rag.faiss_store import RagStoreFaiss, IndexNotFoundError
from ..config import get_settings
from ..schemas.io import Citation
from ..utils.prompt_loader import get_system_prompt, get_query_prompt
from ..utils.llm_client import get_llm_client


class LawRAGAgent:
    """Law and regulation RAG agent for construction safety standards."""
    
    def __init__(self):
        self.settings = get_settings()
        self.rag_store = None
        self.llm = get_llm_client()
        self._initialize_rag_store()
    
    def _initialize_rag_store(self):
        """Initialize the RAG store."""
        try:
            self.rag_store = RagStoreFaiss(
                self.settings.faiss_index_path,
                self.settings.faiss_meta_path
            )
            self.rag_store.load()
        except IndexNotFoundError as e:
            print(f"Warning: FAISS index not found: {e}")
            self.rag_store = None
        except Exception as e:
            print(f"Error initializing RAG store: {e}")
            self.rag_store = None
    
    def search_regulations(self, query: str, work_types: List[str] = None) -> List[Citation]:
        """
        Search for relevant regulations and safety standards with LLM interpretation.
        
        Args:
            query: Search query
            work_types: List of work types to focus on
            
        Returns:
            List of citations with relevant information (LLM-enhanced)
        """
        if not self.rag_store:
            return self._get_fallback_citations(query, work_types)
        
        try:
            # Use prompt-based query formatting
            formatted_query = get_query_prompt(
                "law_rag_query",
                query=query,
                work_types=", ".join(work_types) if work_types else "전체"
            )
            
            # Search the FAISS index
            results = self.rag_store.search(formatted_query, k=self.settings.faiss_top_k)
            
            # Convert to Citation objects
            citations = []
            for result in results:
                citation = Citation(
                    document=result.get("document", "Unknown Document"),
                    page=result.get("page", 0),
                    snippet=result.get("text", ""),
                    score=result.get("score", 0.0)
                )
                citations.append(citation)
            
            # Use LLM to enhance citations with context
            if self.llm.is_available() and citations:
                citations = self._enhance_citations_with_llm(query, citations)
            
            return citations
            
        except Exception as e:
            print(f"Error searching regulations: {e}")
            return self._get_fallback_citations(query, work_types)
    
    def _enhance_citations_with_llm(self, query: str, citations: List[Citation]) -> List[Citation]:
        """Use LLM to enhance and interpret citations."""
        try:
            system_prompt = self.get_system_prompt()
            
            # Prepare citations text
            citations_text = "\n\n".join([
                f"[{i+1}] 문서: {c.document}, 페이지: {c.page}\n내용: {c.snippet}"
                for i, c in enumerate(citations)
            ])
            
            user_prompt = f"""사용자 질문: "{query}"

검색된 법규 내용:
{citations_text}

위 법규 내용을 사용자 질문과 관련하여 핵심만 간략하게 요약해주세요.
각 법규마다 한 줄로 요약하고, 중요한 수치나 기준은 반드시 포함하세요.
형식: [번호] 핵심 내용"""

            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.settings.law_rag_model,
                temperature=self.settings.law_rag_temperature
            )
            
            # Parse LLM response and enhance citations
            enhanced_summaries = response.split("\n")
            for i, citation in enumerate(citations):
                for summary_line in enhanced_summaries:
                    if f"[{i+1}]" in summary_line:
                        # Add LLM summary as a note
                        enhanced_snippet = summary_line.replace(f"[{i+1}]", "").strip()
                        if enhanced_snippet:
                            citation.snippet = f"{enhanced_snippet}\n\n원문: {citation.snippet}"
                        break
            
            return citations
            
        except Exception as e:
            print(f"LLM enhancement error: {e}")
            return citations  # Return original citations on error
    
    def search_by_work_type(self, work_type: str) -> List[Citation]:
        """Search regulations for specific work type."""
        query = f"{work_type} 작업 안전 기준"
        return self.search_regulations(query, [work_type])
    
    def search_weather_conditions(self, condition: str) -> List[Citation]:
        """Search for weather-related safety standards."""
        query = f"{condition} 기상조건 작업중지 기준"
        return self.search_regulations(query)
    
    def search_equipment_standards(self, equipment: str) -> List[Citation]:
        """Search for equipment-specific safety standards."""
        query = f"{equipment} 안전기준 사용규정"
        return self.search_regulations(query)
    
    def _get_fallback_citations(self, query: str, work_types: List[str] = None) -> List[Citation]:
        """Provide fallback citations when FAISS is not available."""
        fallback_citations = [
            Citation(
                document="KOSHA 안전보건기준",
                page=1,
                snippet="작업 중지 기준: 강풍 10m/s 이상, 강우 시 작업 중지",
                score=0.8
            ),
            Citation(
                document="건설업 안전보건규칙",
                page=15,
                snippet="타워크레인 작업 시 풍속 10m/s 이상에서 작업 중지",
                score=0.7
            ),
            Citation(
                document="건설기계 안전관리지침",
                page=23,
                snippet="콘크리트 타설 시 강우 시 작업 중지, 온도 5도 이하 시 작업 중지",
                score=0.6
            )
        ]
        
        # Filter by work type if specified
        if work_types:
            filtered_citations = []
            for citation in fallback_citations:
                for work_type in work_types:
                    if work_type.lower() in citation.snippet.lower():
                        filtered_citations.append(citation)
                        break
            return filtered_citations if filtered_citations else fallback_citations
        
        return fallback_citations
    
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent."""
        return get_system_prompt("law_rag")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status and capabilities."""
        return {
            "name": "Law RAG Agent",
            "faiss_available": self.rag_store is not None,
            "search_capabilities": [
                "regulation_search",
                "work_type_search", 
                "weather_condition_search",
                "equipment_standards_search"
            ],
            "fallback_mode": self.rag_store is None,
            "system_prompt": self.get_system_prompt()
        }
