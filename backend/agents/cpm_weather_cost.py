"""
CPM + Weather + Cost Agent for comprehensive project analysis with LLM-based reasoning.
"""
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import json
from ..schemas.io import WBSItem, DelayRow, CostSummary
from ..tools.services.cpm import CPMService
from ..tools.services.weather import WeatherService
from ..tools.services.holidays import HolidayService
from ..tools.services.cost import CostService
from ..tools.rules.store import RulesStore
from ..config import get_settings
from ..utils.llm_client import get_llm_client


class CPMWeatherCostAgent:
    """Agent for CPM analysis with weather and cost considerations."""
    
    def __init__(self):
        self.cpm_service = CPMService()
        self.weather_service = WeatherService()
        self.holiday_service = HolidayService()
        self.cost_service = CostService()
        self.rules_store = RulesStore()
        self.settings = get_settings()
        self.llm = get_llm_client()
    
    def analyze(self, wbs_json: List[WBSItem], contract_data: Dict[str, Any], rules: List[Any] = None) -> Dict[str, Any]:
        """
        Perform comprehensive project analysis.
        
        Args:
            wbs_json: Parsed WBS items
            contract_data: Contract information
            rules: Extracted rules from threshold builder
            
        Returns:
            Analysis results including CPM, weather impact, and costs
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
        
        # Calculate ideal CPM schedule
        start_date = self._get_start_date(contract_data)
        ideal_schedule = self.cpm_service.compute_cpm(wbs_items, start_date)
        
        # Simulate delays based on weather and rules
        delay_analysis = self._simulate_delays(ideal_schedule, wbs_items, start_date)
        
        # Calculate costs
        cost_analysis = self._calculate_costs(delay_analysis, contract_data)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(delay_analysis, cost_analysis)
        
        return {
            "ideal_schedule": ideal_schedule,
            "delay_analysis": delay_analysis,
            "cost_analysis": cost_analysis,
            "recommendations": recommendations,
            "analysis_timestamp": date.today().isoformat()
        }
    
    def _get_start_date(self, contract_data: Dict[str, Any]) -> date:
        """Get project start date from contract data."""
        if "start_date" in contract_data:
            if isinstance(contract_data["start_date"], str):
                return date.fromisoformat(contract_data["start_date"])
            elif isinstance(contract_data["start_date"], date):
                return contract_data["start_date"]
        
        return date.today()
    
    def _simulate_delays(self, ideal_schedule: Dict[str, Any], wbs_items: List[WBSItem], start_date: date) -> Dict[str, Any]:
        """Simulate delays based on weather and safety rules."""
        project_duration = ideal_schedule.get("project_duration", 0)
        end_date = start_date + timedelta(days=project_duration)
        
        # Get weather forecast
        weather_forecast = self.weather_service.get_weather_forecast(start_date, end_date)
        weather_impact = self.weather_service.get_construction_impact(weather_forecast)
        
        # Get holiday impact
        calendar_policy = "5d"  # Default
        holiday_impact = self.holiday_service.get_holiday_impact(start_date, end_date, calendar_policy)
        
        # Calculate total delays
        weather_delays = weather_impact["unsuitable_days"]
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
    
    def _calculate_costs(self, delay_analysis: Dict[str, Any], contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional costs due to delays."""
        delay_days = delay_analysis.get("total_delay_days", 0)
        
        if delay_days <= 0:
            return {
                "indirect_cost": 0.0,
                "ld": 0.0,
                "total": 0.0,
                "breakdown": [],
                "daily_costs": []
            }
        
        # Calculate costs
        cost_summary = self.cost_service.compute_cost(delay_days, contract_data)
        daily_costs = self.cost_service.compute_daily_costs(delay_days, contract_data)
        
        return {
            "indirect_cost": cost_summary["indirect_cost"],
            "ld": cost_summary["ld"],
            "total": cost_summary["total"],
            "breakdown": cost_summary["breakdown"],
            "daily_costs": daily_costs,
            "delay_days": delay_days
        }
    
    def _generate_recommendations(self, delay_analysis: Dict[str, Any], cost_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis with LLM reasoning."""
        # Try LLM-based recommendations first
        if self.llm.is_available():
            return self._llm_generate_recommendations(delay_analysis, cost_analysis)
        
        # Fallback to rule-based recommendations
        return self._rule_based_recommendations(delay_analysis, cost_analysis)
    
    def _llm_generate_recommendations(self, delay_analysis: Dict[str, Any], cost_analysis: Dict[str, Any]) -> List[str]:
        """Use LLM to generate intelligent recommendations."""
        try:
            delay_days = delay_analysis.get("total_delay_days", 0)
            weather_delays = delay_analysis.get("weather_delays", 0)
            holiday_delays = delay_analysis.get("holiday_delays", 0)
            total_cost = cost_analysis.get("total", 0)
            indirect_cost = cost_analysis.get("indirect_cost", 0)
            ld_cost = cost_analysis.get("ld", 0)
            
            # Get weather forecast details
            weather_forecast = delay_analysis.get("weather_forecast", {})
            delay_rows = delay_analysis.get("delay_rows", [])
            
            # Prepare context for LLM
            context = f"""프로젝트 분석 결과:
- 총 지연일: {delay_days}일
  - 기상 지연: {weather_delays}일
  - 공휴일 지연: {holiday_delays}일
- 추가 비용: {total_cost:,.0f}원
  - 간접비: {indirect_cost:,.0f}원
  - 지연손해금: {ld_cost:,.0f}원

주요 지연 사유:"""
            
            for row in delay_rows[:5]:  # Top 5 delays
                if hasattr(row, 'date'):
                    context += f"\n- {row.date}: {row.reason}"
                else:
                    context += f"\n- {row.get('date', 'N/A')}: {row.get('reason', 'N/A')}"
            
            prompt = f"""{context}

위 분석 결과를 바탕으로 프로젝트 관리자에게 다음을 제공하세요:
1. 핵심 리스크 요약 (1-2줄)
2. 구체적인 대응 방안 3-5가지
3. 비용 절감 또는 일정 단축 아이디어

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
            
            return recommendations if recommendations else self._rule_based_recommendations(delay_analysis, cost_analysis)
            
        except Exception as e:
            print(f"LLM recommendation error: {e}")
            return self._rule_based_recommendations(delay_analysis, cost_analysis)
    
    def _rule_based_recommendations(self, delay_analysis: Dict[str, Any], cost_analysis: Dict[str, Any]) -> List[str]:
        """Fallback rule-based recommendations."""
        recommendations = []
        
        delay_days = delay_analysis.get("total_delay_days", 0)
        total_cost = cost_analysis.get("total", 0)
        
        if delay_days > 0:
            recommendations.append(f"프로젝트 지연 예상: {delay_days}일")
            recommendations.append(f"추가 비용 예상: {self.settings.currency} {total_cost:,.0f}")
            
            if delay_days > 30:
                recommendations.append("장기 지연 예상 - 긴급 대응 방안 수립 필요")
            elif delay_days > 14:
                recommendations.append("중기 지연 예상 - 대응 방안 검토 필요")
            
            # Weather-specific recommendations
            weather_delays = delay_analysis.get("weather_delays", 0)
            if weather_delays > 0:
                recommendations.append("기상 조건으로 인한 지연 예상 - 실내 작업 계획 수립")
            
            # Cost-specific recommendations
            if total_cost > 100000000:  # 1억원 이상
                recommendations.append("높은 추가 비용 예상 - 가속화 방안 검토 필요")
        
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
            "cost_analysis": {
                "indirect_cost": 0.0,
                "ld": 0.0,
                "total": 0.0,
                "breakdown": [],
                "daily_costs": []
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
                "cost_calculation",
                "delay_simulation",
                "recommendation_generation"
            ],
            "services": {
                "cpm": "CPMService",
                "weather": "WeatherService", 
                "holidays": "HolidayService",
                "cost": "CostService"
            }
        }
