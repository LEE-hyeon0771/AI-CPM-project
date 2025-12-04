"""
CPM + Weather Agent for comprehensive project analysis with LLM-based reasoning.
"""
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import json
from ..schemas.io import WBSItem, DelayRow
from ..tools.services.cpm import CPMService
from ..tools.services.weather import WeatherService
from ..tools.services.holidays import HolidayService
from ..tools.rules.store import RulesStore
from ..config import get_settings
from ..utils.llm_client import get_llm_client


class CPMWeatherCostAgent:
    """Agent for CPM analysis with weather and cost considerations."""
    
    def __init__(self):
        self.cpm_service = CPMService()
        self.weather_service = WeatherService()
        self.holiday_service = HolidayService()
        self.rules_store = RulesStore()
        self.settings = get_settings()
        self.llm = get_llm_client()
    
    def analyze(
        self,
        wbs_json: List[WBSItem],
        contract_data: Dict[str, Any],
        rules: List[Any] = None,
        forecast_offset_days: int = 0,
        forecast_duration_days: Optional[int] = None,
        analysis_mode: str = "full",
    ) -> Dict[str, Any]:
        """
        Perform comprehensive project analysis.
        
        Args:
            wbs_json: Parsed WBS items
            contract_data: Contract information
            rules: Extracted rules from threshold builder
            
        Returns:
            Analysis results including CPM and weather/holiday impact
        """
        if not wbs_json:
            return self._get_empty_analysis()
        
        # Convert WBS items if needed
        if isinstance(wbs_json, list) and len(wbs_json) > 0:
            if isinstance(wbs_json[0], dict):
                wbs_items = [WBSItem(**item) for item in wbs_json]
            else:
                wbs_items = wbs_json
        else:
            wbs_items = []
        
        # Calculate ideal CPM schedule (baseline, without delays)
        start_date = self._get_start_date(contract_data)
        ideal_schedule = self.cpm_service.compute_cpm(wbs_items, start_date)
        
        # Determine forecast window for weather/holiday impact
        # analysis_mode:
        # - "initial": 이상적인 CPM만 계산 (날씨/공휴일 API 호출 없음)
        # - "full" 또는 "reforecast": 날씨/공휴일을 반영한 지연 분석 수행
        if forecast_offset_days is None:
            forecast_offset_days = 0
        forecast_start_date = start_date + timedelta(days=forecast_offset_days)
        
        # Simulate delays based on weather and holidays in the chosen window
        if analysis_mode == "initial":
            delay_analysis = self._build_zero_delay_analysis(ideal_schedule)
        else:
            delay_analysis = self._simulate_delays(
                ideal_schedule,
                wbs_items,
                start_date,
                forecast_start_date=forecast_start_date,
                forecast_duration_days=forecast_duration_days,
            )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(delay_analysis)
        
        return {
            "ideal_schedule": ideal_schedule,
            "delay_analysis": delay_analysis,
            "recommendations": recommendations,
            "analysis_timestamp": date.today().isoformat(),
            "analysis_mode": analysis_mode,
        }
    
    def _get_start_date(self, contract_data: Dict[str, Any]) -> date:
        """Get project start date from contract data."""
        if "start_date" in contract_data:
            if isinstance(contract_data["start_date"], str):
                return date.fromisoformat(contract_data["start_date"])
            elif isinstance(contract_data["start_date"], date):
                return contract_data["start_date"]
        
        return date.today()
    
    def _simulate_delays(
        self,
        ideal_schedule: Dict[str, Any],
        wbs_items: List[WBSItem],
        start_date: date,
        forecast_start_date: Optional[date] = None,
        forecast_duration_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Simulate delays based on weather and safety rules."""
        project_duration = ideal_schedule.get("project_duration", 0)

        # ------------------------------
        # 1) 날씨 예보 창 (weather window)
        # ------------------------------
        # - forecast_start_date: 예보 시작일 (기본은 공사 시작일)
        # - forecast_duration_days: 예보 일수 (예: "일주일 후 날씨 반영" → 7일)
        #   * None 또는 0/음수인 경우: 기본적으로 min(프로젝트 기간, 7일)을 사용
        if forecast_start_date is None:
            forecast_start_date = start_date

        if forecast_duration_days is not None and forecast_duration_days > 0:
            weather_end_date = forecast_start_date + timedelta(days=forecast_duration_days - 1)
        else:
            default_window = max(1, min(project_duration, 7))
            weather_end_date = forecast_start_date + timedelta(days=default_window - 1)

        # Get weather forecast only for the chosen weather window
        weather_forecast = self.weather_service.get_weather_forecast(forecast_start_date, weather_end_date)
        weather_impact = self.weather_service.get_construction_impact(weather_forecast)
        
        # ------------------------------
        # 2) 공휴일 + 주말 영향 (holiday/weekend)
        # ------------------------------
        # 사용자가 원하는 의미에 맞춰, 공휴일/주말은
        # "전체 공사 기간(start_date ~ start_date+project_duration-1)" 기준으로 계산한다.
        calendar_policy = "5d"  # Default (월~금 근무)
        full_project_end = start_date + timedelta(days=project_duration - 1) if project_duration > 0 else start_date
        holiday_impact = self.holiday_service.get_holiday_impact(start_date, full_project_end, calendar_policy)
        
        # Calculate total delays
        # 1) 날씨로 인해 "실제로 작업을 못 하는 날"만 카운트하기 위해
        #    주말/공휴일(어차피 비근무일)과 겹치는 날짜는 weather 지연에서 제외한다.
        bad_weather_dates = {
            date.fromisoformat(day["date"])
            for day in weather_forecast["days"]
            if not day["construction_suitable"]
        }

        # non-working days (weekend + holidays) 집합 구성
        holidays_set = {
            date.fromisoformat(d)
            for d in holiday_impact.get("holidays", [])
        }
        non_working_dates = set()
        current = start_date
        while current <= full_project_end:
            is_weekend = current.weekday() >= 5  # 토(5), 일(6)
            is_holiday = current in holidays_set
            if is_weekend or is_holiday:
                non_working_dates.add(current)
            current += timedelta(days=1)

        # 날씨-only 지연일: 비가 오지만 근무일인 날만 카운트
        weather_only_dates = {d for d in bad_weather_dates if d not in non_working_dates}
        weather_delays = len(weather_only_dates)
        weather_total_bad_days = len(bad_weather_dates)
        weather_overlap_nonworking = len(bad_weather_dates & non_working_dates)

        # 주말/공휴일 지연일: 기존 로직 유지 (비근무일 - 법정 공휴일 수)
        holiday_delays = holiday_impact["non_working_days"] - holiday_impact["holiday_count"]

        total_delays = weather_delays + holiday_delays
        
        # Generate delay rows
        delay_rows = []
        current_date = start_date
        cumulative_delay = 0
        
        for day in weather_forecast["days"]:
            day_date = date.fromisoformat(day["date"])
            
            if not day["construction_suitable"]:
                cumulative_delay += 1
                delay_rows.append(DelayRow(
                    date=day_date,
                    reason=day.get("condition", "기상조건 불량"),
                    affected=self._get_affected_tasks(day_date, ideal_schedule),
                    day_delay=1,
                    cumulative=cumulative_delay
                ))
        
        return {
            "total_delay_days": total_delays,
            "weather_delays": weather_delays,
            "weather_total_bad_days": weather_total_bad_days,
            "weather_overlap_nonworking": weather_overlap_nonworking,
            "holiday_delays": holiday_delays,
            "delay_rows": delay_rows,
            "weather_forecast": weather_forecast,
            "holiday_impact": holiday_impact,
            "new_project_duration": project_duration + total_delays
        }
    
    def _get_affected_tasks(self, delay_date: date, ideal_schedule: Dict[str, Any]) -> List[str]:
        """Get tasks affected by delay on specific date."""
        affected_tasks = []
        
        for task in ideal_schedule.get("tasks", []):
            # Simple logic: if task is critical and delay affects its timeline
            if task.get("is_critical", False):
                affected_tasks.append(task["id"])
        
        return affected_tasks
    
    def _build_zero_delay_analysis(self, ideal_schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Build delay analysis dict with no delays (used for initial CPM only)."""
        project_duration = ideal_schedule.get("project_duration", 0)
        return {
            "total_delay_days": 0,
            "weather_delays": 0,
            "holiday_delays": 0,
            "delay_rows": [],
            "weather_forecast": {},
            "holiday_impact": {},
            "new_project_duration": project_duration,
        }
    
    def _generate_recommendations(self, delay_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis with LLM reasoning."""
        # Try LLM-based recommendations first
        if self.llm.is_available():
            return self._llm_generate_recommendations(delay_analysis)
        
        # Fallback to rule-based recommendations
        return self._rule_based_recommendations(delay_analysis)
    
    def _llm_generate_recommendations(self, delay_analysis: Dict[str, Any]) -> List[str]:
        """Use LLM to generate intelligent recommendations."""
        try:
            delay_days = delay_analysis.get("total_delay_days", 0)
            weather_delays = delay_analysis.get("weather_delays", 0)
            holiday_delays = delay_analysis.get("holiday_delays", 0)
            
            # Get weather forecast details
            weather_forecast = delay_analysis.get("weather_forecast", {})
            delay_rows = delay_analysis.get("delay_rows", [])
            
            # Prepare context for LLM
            context = f"""프로젝트 분석 결과:
- 총 지연일: {delay_days}일
  - 기상 지연: {weather_delays}일
  - 공휴일 지연: {holiday_delays}일

주요 지연 사유:"""
            
            for row in delay_rows[:5]:  # Top 5 delays
                if hasattr(row, 'date'):
                    context += f"\n- {row.date}: {row.reason}"
                else:
                    context += f"\n- {row.get('date', 'N/A')}: {row.get('reason', 'N/A')}"
            
            prompt = f"""{context}

위 분석 결과를 바탕으로 프로젝트 관리자에게 다음을 제공하세요:
1. 핵심 일정/지연 리스크 요약 (1-2줄)
2. 구체적인 대응 방안 3-5가지
3. 일정 단축 또는 지연 최소화 아이디어

명확하고 실행 가능한 권장사항을 제시하세요."""

            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": "당신은 건설 프로젝트 관리 전문가입니다. 데이터를 분석하고 실용적인 권장사항을 제공합니다."},
                    {"role": "user", "content": prompt}
                ],
                model=self.settings.cpm_model,
                temperature=self.settings.cpm_temperature
            )
            
            # Parse response into list of recommendations
            recommendations = [line.strip() for line in response.split("\n") if line.strip()]
            
            return recommendations if recommendations else self._rule_based_recommendations(delay_analysis)
            
        except Exception as e:
            print(f"LLM recommendation error: {e}")
            return self._rule_based_recommendations(delay_analysis)
    
    def _rule_based_recommendations(self, delay_analysis: Dict[str, Any]) -> List[str]:
        """Fallback rule-based recommendations."""
        recommendations = []
        
        delay_days = delay_analysis.get("total_delay_days", 0)
        
        if delay_days > 0:
            recommendations.append(f"프로젝트 지연 예상: {delay_days}일")
            
            if delay_days > 30:
                recommendations.append("장기 지연 예상 - 긴급 대응 방안 수립 필요")
            elif delay_days > 14:
                recommendations.append("중기 지연 예상 - 대응 방안 검토 필요")
            
            # Weather-specific recommendations
            weather_delays = delay_analysis.get("weather_delays", 0)
            if weather_delays > 0:
                recommendations.append("기상 조건으로 인한 지연 예상 - 실내 작업 계획 수립")
        
        else:
            recommendations.append("현재 일정으로 진행 가능")
        
        return recommendations
    
    def _get_empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis when no WBS provided."""
        return {
            "ideal_schedule": {"tasks": [], "critical_path": [], "project_duration": 0},
            "delay_analysis": {
                "total_delay_days": 0,
                "weather_delays": 0,
                "holiday_delays": 0,
                "delay_rows": [],
                "new_project_duration": 0
            },
            "recommendations": ["WBS 정보가 필요합니다"],
            "analysis_timestamp": date.today().isoformat()
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status and capabilities."""
        return {
            "name": "CPM Weather Cost Agent",
            "capabilities": [
                "cpm_analysis",
                "weather_impact_analysis",
                "delay_simulation",
                "recommendation_generation"
            ],
            "services": {
                "cpm": "CPMService",
                "weather": "WeatherService", 
                "holidays": "HolidayService"
            }
        }
