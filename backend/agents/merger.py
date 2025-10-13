"""
Merger Agent for unifying outputs and formatting for UI with LLM-based natural language generation.
"""
from typing import List, Dict, Any, Optional
import json
from ..schemas.io import ChatResponse, UITable, UICard, UIResponse, Citation, CostSummary
from ..config import get_settings, format_currency
from ..utils.prompt_loader import get_system_prompt, get_query_prompt
from ..utils.llm_client import get_llm_client


class MergerAgent:
    """Agent for merging and formatting analysis results for UI display."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = get_llm_client()
    
    def merge_results(self, results: Dict[str, Any], contract_data: Dict[str, Any]) -> ChatResponse:
        """
        Merge results from all agents into unified response with LLM-enhanced explanations.
        
        Args:
            results: Results from various agents
            contract_data: Contract information
            
        Returns:
            Unified chat response with natural language explanations
        """
        # Extract results from different agents
        law_rag_results = results.get("law_rag", [])
        threshold_results = results.get("threshold_builder", [])
        cpm_weather_cost_results = results.get("cpm_weather_cost", {})
        
        # Build citations from law RAG results
        citations = self._build_citations(law_rag_results)
        
        # Extract analysis data
        ideal_schedule = cpm_weather_cost_results.get("ideal_schedule", {})
        delay_analysis = cpm_weather_cost_results.get("delay_analysis", {})
        cost_analysis = cpm_weather_cost_results.get("cost_analysis", {})
        
        # Build delay table
        delay_table = self._build_delay_table(delay_analysis)
        
        # Build cost summary
        cost_summary = self._build_cost_summary(cost_analysis)
        
        # Build UI components (with LLM enhancement if available)
        ui_response = self._build_ui_components(
            ideal_schedule, delay_analysis, cost_analysis, threshold_results
        )
        
        # Add LLM-generated natural language summary if available
        if self.llm.is_available():
            ui_response = self._enhance_with_llm_summary(
                ui_response, ideal_schedule, delay_analysis, cost_analysis, citations
            )
        
        return ChatResponse(
            ideal_schedule=ideal_schedule,
            delay_table=delay_table,
            cost_summary=cost_summary,
            citations=citations,
            ui=ui_response
        )
    
    def _enhance_with_llm_summary(
        self, 
        ui_response: UIResponse,
        ideal_schedule: Dict[str, Any],
        delay_analysis: Dict[str, Any],
        cost_analysis: Dict[str, Any],
        citations: List[Citation]
    ) -> UIResponse:
        """Add LLM-generated natural language summary."""
        try:
            # Prepare context
            context = f"""프로젝트 분석 결과:

일정:
- 전체 기간: {ideal_schedule.get('project_duration', 0)}일
- 임계경로: {' → '.join(ideal_schedule.get('critical_path', [])[:5])}
- 작업 수: {len(ideal_schedule.get('tasks', []))}개

지연 분석:
- 총 지연: {delay_analysis.get('total_delay_days', 0)}일
- 기상 지연: {delay_analysis.get('weather_delays', 0)}일
- 공휴일: {delay_analysis.get('holiday_delays', 0)}일
- 새로운 완공일: {delay_analysis.get('new_project_duration', 0)}일

비용:
- 간접비: {cost_analysis.get('indirect_cost', 0):,.0f}원
- 지연손해금: {cost_analysis.get('ld', 0):,.0f}원
- 총 추가비용: {cost_analysis.get('total', 0):,.0f}원

관련 법규: {len(citations)}건"""

            prompt = f"""{context}

위 분석 결과를 프로젝트 관리자가 이해하기 쉽도록 3-4문장으로 요약하세요.
핵심 지연 원인, 비용 영향, 주요 조치사항을 포함하세요."""

            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                model=self.settings.merger_model,
                temperature=self.settings.merger_temperature
            )
            
            # Add summary as a card
            summary_card = UICard(
                title="💡 종합 분석",
                value="AI 분석 요약",
                subtitle=response
            )
            
            ui_response.cards.insert(0, summary_card)  # Add at the beginning
            
            return ui_response
            
        except Exception as e:
            print(f"LLM summary error: {e}")
            return ui_response
    
    def _build_citations(self, law_rag_results: List[Citation]) -> List[Citation]:
        """Build citations from law RAG results."""
        if not law_rag_results:
            return []
        
        # Sort by score and limit to top results
        sorted_citations = sorted(law_rag_results, key=lambda x: x.score or 0, reverse=True)
        return sorted_citations[:5]  # Top 5 citations
    
    def _build_delay_table(self, delay_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Build delay analysis table."""
        delay_rows = delay_analysis.get("delay_rows", [])
        
        return {
            "total_delay_days": delay_analysis.get("total_delay_days", 0),
            "weather_delays": delay_analysis.get("weather_delays", 0),
            "holiday_delays": delay_analysis.get("holiday_delays", 0),
            "new_project_duration": delay_analysis.get("new_project_duration", 0),
            "delay_rows": [
                {
                    "date": row.date.isoformat() if hasattr(row, 'date') else str(row.get("date", "")),
                    "reason": row.reason if hasattr(row, 'reason') else str(row.get("reason", "")),
                    "affected": row.affected if hasattr(row, 'affected') else row.get("affected", []),
                    "day_delay": row.day_delay if hasattr(row, 'day_delay') else row.get("day_delay", 0),
                    "cumulative": row.cumulative if hasattr(row, 'cumulative') else row.get("cumulative", 0)
                }
                for row in delay_rows
            ]
        }
    
    def _build_cost_summary(self, cost_analysis: Dict[str, Any]) -> CostSummary:
        """Build cost summary."""
        return CostSummary(
            indirect_cost=cost_analysis.get("indirect_cost", 0.0),
            ld=cost_analysis.get("ld", 0.0),
            total=cost_analysis.get("total", 0.0)
        )
    
    def _build_ui_components(self, ideal_schedule: Dict[str, Any], delay_analysis: Dict[str, Any], 
                           cost_analysis: Dict[str, Any], threshold_results: List[Any]) -> UIResponse:
        """Build UI tables and cards."""
        tables = []
        cards = []
        
        # Build ideal schedule table
        if ideal_schedule.get("tasks"):
            tables.append(self._build_schedule_table(ideal_schedule))
        
        # Build delay analysis table
        if delay_analysis.get("delay_rows"):
            tables.append(self._build_delay_analysis_table(delay_analysis))
        
        # Build cost cards
        cards.extend(self._build_cost_cards(cost_analysis))
        
        # Build summary cards
        cards.extend(self._build_summary_cards(ideal_schedule, delay_analysis))
        
        # Build rules cards
        if threshold_results:
            cards.extend(self._build_rules_cards(threshold_results))
        
        return UIResponse(tables=tables, cards=cards)
    
    def _build_schedule_table(self, ideal_schedule: Dict[str, Any]) -> UITable:
        """Build ideal schedule table."""
        headers = ["작업ID", "작업명", "기간(일)", "작업유형", "ES", "EF", "LS", "LF", "TF", "임계경로"]
        rows = []
        
        for task in ideal_schedule.get("tasks", []):
            row = [
                task.get("id", ""),
                task.get("name", ""),
                task.get("duration", 0),
                task.get("work_type", ""),
                task.get("es", 0),
                task.get("ef", 0),
                task.get("ls", 0),
                task.get("lf", 0),
                task.get("tf", 0),
                "예" if task.get("is_critical", False) else "아니오"
            ]
            rows.append(row)
        
        return UITable(
            title="이상 일정 (CPM 분석)",
            headers=headers,
            rows=rows
        )
    
    def _build_delay_analysis_table(self, delay_analysis: Dict[str, Any]) -> UITable:
        """Build delay analysis table."""
        headers = ["날짜", "지연사유", "영향작업", "일일지연", "누적지연"]
        rows = []
        
        for delay_row in delay_analysis.get("delay_rows", []):
            if hasattr(delay_row, 'date'):
                date_str = delay_row.date.isoformat()
                reason = delay_row.reason
                affected = ", ".join(delay_row.affected)
                day_delay = delay_row.day_delay
                cumulative = delay_row.cumulative
            else:
                date_str = str(delay_row.get("date", ""))
                reason = str(delay_row.get("reason", ""))
                affected = ", ".join(delay_row.get("affected", []))
                day_delay = delay_row.get("day_delay", 0)
                cumulative = delay_row.get("cumulative", 0)
            
            row = [date_str, reason, affected, day_delay, cumulative]
            rows.append(row)
        
        return UITable(
            title="지연 분석",
            headers=headers,
            rows=rows
        )
    
    def _build_cost_cards(self, cost_analysis: Dict[str, Any]) -> List[UICard]:
        """Build cost-related cards."""
        cards = []
        
        total_cost = cost_analysis.get("total", 0)
        indirect_cost = cost_analysis.get("indirect_cost", 0)
        ld_cost = cost_analysis.get("ld", 0)
        delay_days = cost_analysis.get("delay_days", 0)
        
        cards.append(UICard(
            title="총 추가 비용",
            value=format_currency(total_cost),
            subtitle=f"{delay_days}일 지연 기준"
        ))
        
        cards.append(UICard(
            title="간접비",
            value=format_currency(indirect_cost),
            subtitle=f"일일 {format_currency(cost_analysis.get('indirect_cost_per_day', 0))}"
        ))
        
        cards.append(UICard(
            title="지연손해금",
            value=format_currency(ld_cost),
            subtitle="계약 조건 기준"
        ))
        
        return cards
    
    def _build_summary_cards(self, ideal_schedule: Dict[str, Any], delay_analysis: Dict[str, Any]) -> List[UICard]:
        """Build summary cards."""
        cards = []
        
        # Project duration
        original_duration = ideal_schedule.get("project_duration", 0)
        new_duration = delay_analysis.get("new_project_duration", original_duration)
        delay_days = new_duration - original_duration
        
        cards.append(UICard(
            title="프로젝트 기간",
            value=f"{new_duration}일",
            subtitle=f"원래 {original_duration}일 → {delay_days}일 지연"
        ))
        
        # Critical path
        critical_path = ideal_schedule.get("critical_path", [])
        cards.append(UICard(
            title="임계경로",
            value=f"{len(critical_path)}개 작업",
            subtitle="→".join(critical_path[:3]) + ("..." if len(critical_path) > 3 else "")
        ))
        
        # Weather impact
        weather_delays = delay_analysis.get("weather_delays", 0)
        cards.append(UICard(
            title="기상 지연",
            value=f"{weather_delays}일",
            subtitle="예상 기상 조건 불량일"
        ))
        
        return cards
    
    def _build_rules_cards(self, threshold_results: List[Any]) -> List[UICard]:
        """Build rules-related cards."""
        cards = []
        
        if not threshold_results:
            return cards
        
        # Count rules by work type
        work_type_counts = {}
        for rule in threshold_results:
            work_type = rule.work_type if hasattr(rule, 'work_type') else rule.get("work_type", "GENERAL")
            work_type_counts[work_type] = work_type_counts.get(work_type, 0) + 1
        
        # Create cards for top work types
        for work_type, count in sorted(work_type_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
            cards.append(UICard(
                title=f"{work_type} 규칙",
                value=f"{count}개",
                subtitle="추출된 안전 기준"
            ))
        
        return cards
    
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent."""
        return get_system_prompt("merger")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status and capabilities."""
        return {
            "name": "Merger Agent",
            "capabilities": [
                "result_merging",
                "ui_table_generation",
                "ui_card_generation",
                "citation_formatting",
                "cost_formatting"
            ],
            "output_formats": [
                "ChatResponse",
                "UITable",
                "UICard",
                "UIResponse"
            ],
            "system_prompt": self.get_system_prompt()
        }
