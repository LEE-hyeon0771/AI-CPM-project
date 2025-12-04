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
        analysis_mode = cpm_weather_cost_results.get("analysis_mode", "full")
        tasks = ideal_schedule.get("tasks", [])
        wbs_work_types = list({
            (t.get("work_type") or "GENERAL") for t in tasks if isinstance(t, dict)
        })
        
        # Build delay table
        delay_table = self._build_delay_table(delay_analysis)
        
        # Build UI components (with LLM enhancement if available)
        ui_response = self._build_ui_components(
            ideal_schedule, delay_analysis, analysis_mode, threshold_results, wbs_work_types
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

                prompt = f"""당신은 건설 안전/법규 전문가입니다.

아래는 검색된 법규/규정 요약입니다:
{citations_text}

아래 템플릿 형식을 **그대로** 사용하여, 공사/작업 담당자가 이해하기 쉬운 요약을 작성하세요.
특히 풍속, 온도, 강우량 등 수치 기준이 있으면 숫자와 단위를 반드시 포함하세요.

형식 템플릿 (이 구조와 제목은 그대로 유지하고 내용을 채우세요):

**요약 정보:**
1. 핵심 법규/기준 요약 (1~2문장)
2. 가장 중요한 수치 기준 또는 조건 정리

**상세 분석:**
- 각 법규가 의미하는 바와, 서로 어떻게 보완/연결되는지 설명
- 현장에서 주의해야 할 작업 조건(풍속, 온도, 강우 등) 정리

**시각적 요소:**
- 테이블: 적용 작업 종류, 기준값, 단위 등을 정리하면 좋음
- 카드: 가장 중요한 1~3개의 기준값 강조

**실행 방안:**
- 현장에서 이 기준을 어떻게 적용해야 하는지
- 작업 중지/재개 판단 시 참고 절차
- 추가로 확인해야 할 문서나 담당 부서 제안

위 템플릿 구조만 사용하고, 다른 설명은 추가하지 마세요."""

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

아래 템플릿 형식을 **그대로** 사용하여, 프로젝트 관리자용 종합 분석을 작성하세요.

형식 템플릿 (이 구조와 제목은 그대로 유지하고 내용을 채우세요):

**요약 정보:**
1. 공사 기간이 원래 기간 대비 얼마나 늘어났는지 (총 {delay_days}일 증가 등 구체적 숫자 포함)
2. 지연의 주요 원인(기상, 공휴일 등)이 무엇이며 각각 며칠 정도인지
3. 일정/리스크 측면에서 한눈에 볼 수 있는 핵심 포인트

**상세 분석:**
- 이상 일정(CPM 기준)과 날씨/휴일 반영 일정의 차이 설명
- 임계경로 상 어떤 작업들이 민감한지, 지연이 어디에 집중되는지
- 기상 지연/공휴일 지연이 작업 순서에 미치는 영향

**시각적 요소:**
- 테이블: 이상 일정, 날씨 반영 일정, 지연 분석 테이블에서 무엇을 보면 좋은지 안내
- 카드: 총 공사 기간, 공휴일 지연, 날씨 지연, 임계경로 카드 각각이 의미하는 바

**실행 방안:**
- 공휴일/날씨를 고려한 일정 재조정 방향
- 임계경로 상 작업에 대한 우선순위 조정 및 리소스 배분 전략
- 향후 유사 프로젝트에서 참고할 수 있는 교훈 또는 체크리스트

위 템플릿 구조만 사용하고, 다른 설명은 추가하지 마세요."""

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
                           analysis_mode: str, threshold_results: List[Any],
                           wbs_work_types: List[str]) -> UIResponse:
        """Build UI tables and cards."""
        # 법규 전용 모드(law_only)인 경우에는 CPM/지연 관련 테이블/카드는 만들지 않는다.
        # 대신 LLM 요약 카드(💡 법규 설명 등)는 _enhance_with_llm_summary 에서 추가된다.
        if analysis_mode == "law_only":
            return UIResponse(tables=[], cards=[])
        tables = []
        cards = []
        
        # Build ideal schedule table (always)
        if ideal_schedule.get("tasks"):
            tables.append(self._build_schedule_table(ideal_schedule))
        
        # Only show weather/holiday-related tables and cards for non-initial analysis
        if analysis_mode != "initial":
            weather_adjusted_table = self._build_weather_adjusted_schedule_table(ideal_schedule, delay_analysis)
            if weather_adjusted_table is not None:
                tables.append(weather_adjusted_table)
            
            if delay_analysis.get("delay_rows"):
                tables.append(self._build_delay_analysis_table(delay_analysis))

        # Build summary cards
        cards.extend(self._build_summary_cards(ideal_schedule, delay_analysis, analysis_mode))
        
        # Build rules cards
        if threshold_results:
            cards.extend(self._build_rules_cards(threshold_results, wbs_work_types))
        
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
            "LS(원안)",
            "LF(원안)",
            "TF(원안)",
            "ES(날씨 반영)",
            "EF(날씨 반영)",
            "LS(날씨 반영)",
            "LF(날씨 반영)",
            "임계경로",
        ]
        rows = []

        for task in tasks:
            es = task.get("es", 0)
            ef = task.get("ef", 0)
            ls = task.get("ls", 0)
            lf = task.get("lf", 0)
            tf = task.get("tf", 0)
            is_critical = task.get("is_critical", False)

            if is_critical:
                adj_es = es + delay_days
                adj_ef = ef + delay_days
                adj_ls = ls + delay_days
                adj_lf = lf + delay_days
            else:
                adj_es = es
                adj_ef = ef
                adj_ls = ls
                adj_lf = lf

            row = [
                task.get("id", ""),
                task.get("name", ""),
                task.get("duration", 0),
                task.get("work_type", ""),
                es,
                ef,
                ls,
                lf,
                tf,
                adj_es,
                adj_ef,
                adj_ls,
                adj_lf,
                "예" if is_critical else "아니오"
            ]
            rows.append(row)

        return UITable(
            title="날씨 반영 일정표",
            headers=headers,
            rows=rows
        )
    
    def _build_summary_cards(self, ideal_schedule: Dict[str, Any], delay_analysis: Dict[str, Any],
                             analysis_mode: str) -> List[UICard]:
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
        
        if analysis_mode != "initial":
            # Holiday impact
            holiday_delays = delay_analysis.get("holiday_delays", 0)
            # 날씨 영향 세부 수치
            weather_delays = delay_analysis.get("weather_delays", 0)
            weather_total_bad_days = delay_analysis.get("weather_total_bad_days", weather_delays)
            weather_overlap_nonworking = delay_analysis.get("weather_overlap_nonworking", 0)

            cards.append(UICard(
                title="공휴일 지연",
                value=f"{holiday_delays}일",
                subtitle="공휴일/비근무일로 인한 지연"
            ))
            
            # Weather impact
            weather_subtitle_parts = [f"예상 기상 조건 불량일 {weather_total_bad_days}일"]
            if weather_overlap_nonworking > 0:
                weather_subtitle_parts.append(
                    f"(이 중 {weather_overlap_nonworking}일은 주말/공휴일과 겹쳐 추가 지연 없음)"
                )

            cards.append(UICard(
                title="날씨 지연",
                value=f"{weather_delays}일",
                subtitle="; ".join(weather_subtitle_parts)
            ))
        
        # Critical path
        critical_path = ideal_schedule.get("critical_path", [])
        cards.append(UICard(
            title="임계경로",
            value=f"{len(critical_path)}개 작업",
            subtitle="→".join(critical_path[:3]) + ("..." if len(critical_path) > 3 else "")
        ))
        
        return cards
    
    def _build_rules_cards(self, threshold_results: List[Any], wbs_work_types: List[str]) -> List[UICard]:
        """Build rules-related cards."""
        cards = []
        
        if not threshold_results:
            return cards

        # WBS에 등장한 작업 유형 + GENERAL 만 허용
        allowed_work_types = set(wbs_work_types or [])
        allowed_work_types.add("GENERAL")

        # Collect unique regulation snippets from rules (derived from FAISS citations)
        snippets = []
        seen_sources = set()
        for rule in threshold_results:
            work_type = rule.work_type if hasattr(rule, "work_type") else rule.get("work_type", "GENERAL")
            if work_type not in allowed_work_types:
                continue

            src = rule.source if hasattr(rule, "source") else rule.get("source", {})
            key = (src.get("document"), src.get("page"), src.get("snippet"))
            if key in seen_sources:
                continue
            seen_sources.add(key)
            if src.get("snippet"):
                doc = src.get("document", "Unknown")
                page = src.get("page", 0)
                text = src.get("snippet", "")
                snippets.append(f"- [{doc} p.{page}] {text}")
        
        # Limit number of snippets to avoid overly long card
        snippets = snippets[:5]
        subtitle = "\n".join(snippets) if snippets else "관련 안전 규정을 찾지 못했습니다."

        cards.append(UICard(
            title="안전규정",
            value="작업별 안전 기준",
            subtitle=subtitle
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
