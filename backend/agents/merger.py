"""
Merger Agent for unifying outputs and formatting for UI with LLM-based natural language generation.
"""
from typing import List, Dict, Any, Optional
import json
from ..schemas.io import ChatResponse, UITable, UICard, UIResponse, Citation
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
        
        # Build delay table
        delay_table = self._build_delay_table(delay_analysis)
        
        # Build UI components (with LLM enhancement if available)
        ui_response = self._build_ui_components(
            ideal_schedule, delay_analysis, threshold_results
        )
        
        # Add LLM-generated natural language summary if available
        if self.llm.is_available():
            ui_response = self._enhance_with_llm_summary(
                ui_response, ideal_schedule, delay_analysis, citations
            )
        
        return ChatResponse(
            ideal_schedule=ideal_schedule,
            delay_table=delay_table,
            citations=citations,
            ui=ui_response
        )
    
    def _enhance_with_llm_summary(
        self,
        ui_response: UIResponse,
        ideal_schedule: Dict[str, Any],
        delay_analysis: Dict[str, Any],
        citations: List[Citation]
    ) -> UIResponse:
        """Add LLM-generated natural language summary."""
        try:
            original_duration = ideal_schedule.get("project_duration", 0)
            new_duration = delay_analysis.get("new_project_duration", original_duration)
            delay_days = max(0, new_duration - original_duration)

            total_delay = delay_analysis.get("total_delay_days", 0)
            weather_delays = delay_analysis.get("weather_delays", 0)
            holiday_delays = delay_analysis.get("holiday_delays", 0)

            # 규정 질문 등으로 CPM 데이터가 거의 없는 경우: 법규 중심 요약
            if original_duration == 0 and total_delay == 0 and citations:
                citations_text = "\n\n".join(
                    f"[{i+1}] 문서: {c.document}, 페이지: {c.page}\n내용: {c.snippet}"
                    for i, c in enumerate(citations)
                )

                prompt = f"""사용자에게 관련 법규와 기준을 이해하기 쉽게 설명해야 합니다.

검색된 법규/규정 요약:
{citations_text}

위 내용을 바탕으로, 공사/작업 담당자가 바로 이해할 수 있도록 3-4문장으로 설명하세요.
- 핵심 수치나 기준(풍속, 온도 등)이 있다면 숫자와 단위를 꼭 포함하세요.
- 실제 현장에서 어떻게 적용해야 하는지도 간단히 덧붙이세요."""

                response = self.llm.chat_completion(
                    messages=[
                        {"role": "system", "content": self.get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.settings.merger_model,
                    temperature=self.settings.merger_temperature
                )

                summary_card = UICard(
                    title="💡 법규 설명",
                    value="AI 법규 요약",
                    subtitle=response
                )
                ui_response.cards.insert(0, summary_card)
                return ui_response

            # 일반 CPM + 지연 분석 요약
            context = f"""프로젝트 분석 결과:

일정:
- 원래 기간: {original_duration}일
- 날씨/휴일 반영 후 기간: {new_duration}일 (총 {delay_days}일 증가)
- 임계경로: {' → '.join(ideal_schedule.get('critical_path', [])[:5])}
- 작업 수: {len(ideal_schedule.get('tasks', []))}개

지연 분석:
- 총 지연: {total_delay}일
- 기상 지연: {weather_delays}일
- 공휴일: {holiday_delays}일
- 새로운 완공 기간: {delay_analysis.get('new_project_duration', 0)}일

관련 법규: {len(citations)}건"""

            prompt = f"""{context}

위 분석 결과와 공정표를 바탕으로 다음을 3-4문장으로 명확하게 설명하세요:
1. 공사 기간이 총 몇 일 늘어났는지 (원래 기간 대비 비교 포함)
2. 어떤 이유(기상 조건, 공휴일 등)로 각각 몇 일 정도 늘어났는지
3. 일정 관리 관점에서 취해야 할 주요 대응 방안"""

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
    
    def _build_ui_components(self, ideal_schedule: Dict[str, Any], delay_analysis: Dict[str, Any],
                           threshold_results: List[Any]) -> UIResponse:
        """Build UI tables and cards."""
        tables = []
        cards = []
        
        # Build ideal schedule table
        if ideal_schedule.get("tasks"):
            tables.append(self._build_schedule_table(ideal_schedule))
        
        # Build weather-adjusted schedule table if there are delays
        weather_adjusted_table = self._build_weather_adjusted_schedule_table(ideal_schedule, delay_analysis)
        if weather_adjusted_table is not None:
            tables.append(weather_adjusted_table)
        
        # Build delay analysis table
        if delay_analysis.get("delay_rows"):
            tables.append(self._build_delay_analysis_table(delay_analysis))

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

    def _build_weather_adjusted_schedule_table(self, ideal_schedule: Dict[str, Any], delay_analysis: Dict[str, Any]) -> Optional[UITable]:
        """Build weather-adjusted schedule table based on total delay days.

        단순화된 가정: 총 지연일수를 임계경로(critical path) 작업의 ES/EF에만 일괄적으로 더해
        '날씨 반영 일정'을 계산한다. 비임계 작업은 원래 일정 유지.
        """
        tasks = ideal_schedule.get("tasks", [])
        if not tasks:
            return None

        delay_days = delay_analysis.get("total_delay_days", 0)
        if delay_days <= 0:
            return None

        headers = [
            "작업ID",
            "작업명",
            "기간(일)",
            "작업유형",
            "ES(원안)",
            "EF(원안)",
            "ES(날씨 반영)",
            "EF(날씨 반영)",
            "임계경로"
        ]
        rows = []

        for task in tasks:
            es = task.get("es", 0)
            ef = task.get("ef", 0)
            is_critical = task.get("is_critical", False)

            if is_critical:
                adj_es = es + delay_days
                adj_ef = ef + delay_days
            else:
                adj_es = es
                adj_ef = ef

            row = [
                task.get("id", ""),
                task.get("name", ""),
                task.get("duration", 0),
                task.get("work_type", ""),
                es,
                ef,
                adj_es,
                adj_ef,
                "예" if is_critical else "아니오"
            ]
            rows.append(row)

        return UITable(
            title="날씨 반영 일정표",
            headers=headers,
            rows=rows
        )
    
    def _build_summary_cards(self, ideal_schedule: Dict[str, Any], delay_analysis: Dict[str, Any]) -> List[UICard]:
        """Build summary cards."""
        cards = []
        
        # Project duration
        original_duration = ideal_schedule.get("project_duration", 0)
        new_duration = delay_analysis.get("new_project_duration", original_duration)
        delay_days = max(0, new_duration - original_duration)
        
        cards.append(UICard(
            title="총 공사 기간",
            value=f"{new_duration}일",
            subtitle=f"원래 {original_duration}일 기준, +{delay_days}일 지연"
        ))
        
        # Holiday impact
        holiday_delays = delay_analysis.get("holiday_delays", 0)
        cards.append(UICard(
            title="공휴일 지연",
            value=f"{holiday_delays}일",
            subtitle="공휴일/비근무일로 인한 지연"
        ))
        
        # Weather impact
        weather_delays = delay_analysis.get("weather_delays", 0)
        cards.append(UICard(
            title="날씨 지연",
            value=f"{weather_delays}일",
            subtitle="예상 기상 조건 불량일"
        ))
        
        # Critical path
        critical_path = ideal_schedule.get("critical_path", [])
        cards.append(UICard(
            title="임계경로",
            value=f"{len(critical_path)}개 작업",
            subtitle="→".join(critical_path[:3]) + ("..." if len(critical_path) > 3 else "")
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
                "citation_formatting"
            ],
            "output_formats": [
                "ChatResponse",
                "UITable",
                "UICard",
                "UIResponse"
            ],
            "system_prompt": self.get_system_prompt()
        }
