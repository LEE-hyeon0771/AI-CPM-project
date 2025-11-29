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

        # Work type → 실제 한글 공종/작업명 키워드 매핑 (메타데이터 강화)
        # WBS에서 쓰는 코드(EARTHWORK, CONCRETE 등)를
        # FAISS 메타/본문에 등장하는 한글 표현과 연결해 검색 품질을 높인다.
        self.work_type_keywords = {
            "EARTHWORK": ["토공", "기초 토공", "굴착", "흙막이", "토사 제거", "기초 공사", "말뚝"],
            "CONCRETE": ["콘크리트", "기초 콘크리트", "기초 타설", "구조 골조", "골조 콘크리트", "슬래브 타설"],
            "STEEL": ["철골", "강재", "강구조", "철골 구조", "철골 조립"],
            "FINISHING": ["마감", "마감공사", "내부 마감", "외부 마감", "타일", "도장"],
            "CRANE": ["크레인", "타워크레인", "호이스트"],
            "ELECTRICAL": ["전기", "배선", "조명", "전력"],
            "PLUMBING": ["배관", "급수", "배수", "상하수도"],
            "GENERAL": ["건설 공사", "작업 전반", "현장 일반"],
        }
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
            # 작업 유형을 한글 공종/작업명 키워드로 확장
            expanded_terms: List[str] = []
            if work_types:
                for wt in work_types:
                    if wt in self.work_type_keywords:
                        expanded_terms.extend(self.work_type_keywords[wt])
                    else:
                        expanded_terms.append(wt)
            work_types_str = ", ".join(sorted(set(expanded_terms))) if expanded_terms else "전체"

            # Use prompt-based query formatting
            # get_query_prompt(agent_name) 가 내부에서 "<agent_name>_query.txt" 를 찾으므로
            # 여기서는 단순히 "law_rag" 만 넘긴다.
            # 기존 "law_rag_query" 는 "law_rag_query_query.txt" 를 찾게 되어
            # 프롬프트 파일을 못 찾는 문제가 있었다.
            formatted_query = get_query_prompt(
                "law_rag",
                query=query,
                work_types=work_types_str
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
        
        # Filter by work type (확장된 한글 키워드 기준) if specified
        if work_types:
            # work_types 코드(EARTHWORK 등)를 한글 키워드로 확장
            expanded_terms: List[str] = []
            for wt in work_types:
                if wt in self.work_type_keywords:
                    expanded_terms.extend(self.work_type_keywords[wt])
                else:
                    expanded_terms.append(wt)

            lowered_terms = [t.lower() for t in expanded_terms]

            filtered_citations = []
            for citation in fallback_citations:
                text = f"{citation.document} {citation.snippet}".lower()
                if any(term in text for term in lowered_terms):
                    filtered_citations.append(citation)

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
