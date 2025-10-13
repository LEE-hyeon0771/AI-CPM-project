"""
Supervisor agent for intent routing and orchestration.
"""
from typing import Dict, Any, List
import re
import json
from .config import get_settings
from .utils.prompt_loader import get_system_prompt
from .utils.llm_client import get_llm_client


class Supervisor:
    """Supervisor agent that routes intents to appropriate agents."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = get_llm_client()
        self.intent_patterns = {
            "law_regulation": [
                r"법규|규정|기준|안전|KOSHA|코샤",
                r"타워크레인|크레인|풍속|바람",
                r"작업중지|중지기준|기상조건"
            ],
            "threshold": [
                r"임계값|기준값|threshold|기준",
                r"수치|값|규칙"
            ],
            "schedule": [
                r"일정|스케줄|CPM|공정|진도",
                r"지연|연기|delay|공기"
            ],
            "weather": [
                r"날씨|기상|예보|비|바람|폭우",
                r"기상조건|날씨조건"
            ],
            "cost": [
                r"비용|원가|손해|배상|간접비",
                r"cost|금액|돈"
            ]
        }
    
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent."""
        return get_system_prompt("supervisor")
    
    def route_intent(self, message: str) -> Dict[str, Any]:
        """
        Route user message to appropriate agents based on intent analysis.
        
        Args:
            message: User input message
            
        Returns:
            Dict containing routing information and required agents
        """
        # Try LLM-based routing first
        if self.llm.is_available():
            return self._llm_route_intent(message)
        
        # Fallback to regex-based routing
        return self._regex_route_intent(message)
    
    def _llm_route_intent(self, message: str) -> Dict[str, Any]:
        """LLM-based intent routing."""
        system_prompt = self.get_system_prompt()
        
        user_prompt = f"""사용자 메시지를 분석하여 필요한 에이전트를 결정하세요.

사용자 메시지: "{message}"

사용 가능한 에이전트:
- law_rag: 법규, 규정, 안전 기준 검색
- threshold_builder: 법규에서 수치 기준 추출
- cpm_weather_cost: 일정 분석, 날씨 영향, 비용 계산

다음 JSON 형식으로 응답하세요:
{{
    "intents": ["의도1", "의도2"],
    "required_agents": ["agent1", "agent2"],
    "reasoning": "선택 이유"
}}"""

        try:
            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.settings.supervisor_model,
                temperature=self.settings.supervisor_temperature
            )
            
            # Parse JSON response
            result = json.loads(response)
            
            # Always include merger
            if "merger" not in result["required_agents"]:
                result["required_agents"].append("merger")
            
            result["message"] = message
            result["analysis_type"] = "llm_based"
            
            return result
            
        except Exception as e:
            print(f"LLM routing error: {e}")
            return self._regex_route_intent(message)
    
    def _regex_route_intent(self, message: str) -> Dict[str, Any]:
        """Regex-based fallback routing."""
        message_lower = message.lower()
        
        # Analyze intent
        detected_intents = []
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    detected_intents.append(intent)
                    break
        
        # Determine required agents
        required_agents = []
        
        if "law_regulation" in detected_intents or "threshold" in detected_intents:
            required_agents.extend(["law_rag", "threshold_builder"])
        
        if "schedule" in detected_intents or "weather" in detected_intents:
            required_agents.append("cpm_weather_cost")
        
        if "cost" in detected_intents:
            required_agents.append("cpm_weather_cost")
        
        # If no specific intent detected, default to full analysis
        if not required_agents:
            required_agents = ["law_rag", "threshold_builder", "cpm_weather_cost"]
        
        # Always include merger for final formatting
        required_agents.append("merger")
        
        return {
            "intents": detected_intents,
            "required_agents": list(set(required_agents)),
            "message": message,
            "analysis_type": "regex_based"
        }
    
    def should_parse_wbs(self, wbs_text: str) -> bool:
        """Determine if WBS parsing is needed."""
        return wbs_text is not None and len(wbs_text.strip()) > 0
    
    def extract_work_types(self, wbs_text: str) -> List[str]:
        """Extract work types from WBS text for targeted RAG search."""
        work_types = []
        
        # Common work type patterns
        work_type_patterns = {
            "EARTHWORK": [r"토공|굴착|땅파기|지반"],
            "CONCRETE": [r"콘크리트|타설|거푸집"],
            "CRANE": [r"크레인|타워크레인|호이스트"],
            "STEEL": [r"철골|강재|구조"],
            "ELECTRICAL": [r"전기|배선|전력"],
            "PLUMBING": [r"배관|상하수도|급수"]
        }
        
        for work_type, patterns in work_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, wbs_text, re.IGNORECASE):
                    work_types.append(work_type)
                    break
        
        return work_types
