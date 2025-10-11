"""
Cost calculation service for construction projects.
"""
from typing import Dict, Any, List
from datetime import date, timedelta
from ...config import get_settings, format_currency


class CostService:
    """Cost calculation service for construction projects."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def compute_cost(self, delay_days: int, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute additional costs due to project delays.
        
        Args:
            delay_days: Number of delay days
            contract_data: Contract information
            
        Returns:
            Cost analysis results
        """
        if delay_days <= 0:
            return {
                "indirect_cost": 0.0,
                "ld": 0.0,
                "total": 0.0,
                "breakdown": []
            }
        
        # Extract contract parameters
        contract_amount = contract_data.get("contract_amount", 0)
        ld_rate = contract_data.get("ld_rate", 0.0005)  # Default 0.05% per day
        indirect_cost_per_day = contract_data.get("indirect_cost_per_day", 0)
        
        # Calculate indirect costs
        indirect_cost = delay_days * indirect_cost_per_day
        
        # Calculate liquidated damages
        ld = delay_days * contract_amount * ld_rate
        
        # Total additional cost
        total = indirect_cost + ld
        
        # Cost breakdown
        breakdown = [
            {
                "type": "간접비",
                "description": f"일일 간접비 × {delay_days}일",
                "amount": indirect_cost,
                "formatted": format_currency(indirect_cost)
            },
            {
                "type": "지연손해금",
                "description": f"계약금액 × {ld_rate:.4f} × {delay_days}일",
                "amount": ld,
                "formatted": format_currency(ld)
            }
        ]
        
        return {
            "indirect_cost": indirect_cost,
            "ld": ld,
            "total": total,
            "breakdown": breakdown,
            "delay_days": delay_days,
            "formatted": {
                "indirect_cost": format_currency(indirect_cost),
                "ld": format_currency(ld),
                "total": format_currency(total)
            }
        }
    
    def compute_daily_costs(self, delay_days: int, contract_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compute daily cost breakdown."""
        if delay_days <= 0:
            return []
        
        daily_costs = []
        contract_amount = contract_data.get("contract_amount", 0)
        ld_rate = contract_data.get("ld_rate", 0.0005)
        indirect_cost_per_day = contract_data.get("indirect_cost_per_day", 0)
        
        cumulative_indirect = 0
        cumulative_ld = 0
        
        for day in range(1, delay_days + 1):
            daily_indirect = indirect_cost_per_day
            daily_ld = contract_amount * ld_rate
            
            cumulative_indirect += daily_indirect
            cumulative_ld += daily_ld
            
            daily_costs.append({
                "day": day,
                "daily_indirect": daily_indirect,
                "daily_ld": daily_ld,
                "daily_total": daily_indirect + daily_ld,
                "cumulative_indirect": cumulative_indirect,
                "cumulative_ld": cumulative_ld,
                "cumulative_total": cumulative_indirect + cumulative_ld,
                "formatted": {
                    "daily_indirect": format_currency(daily_indirect),
                    "daily_ld": format_currency(daily_ld),
                    "daily_total": format_currency(daily_indirect + daily_ld),
                    "cumulative_indirect": format_currency(cumulative_indirect),
                    "cumulative_ld": format_currency(cumulative_ld),
                    "cumulative_total": format_currency(cumulative_indirect + cumulative_ld)
                }
            })
        
        return daily_costs
    
    def analyze_cost_impact(self, original_schedule: Dict[str, Any], delayed_schedule: Dict[str, Any], contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cost impact of schedule changes."""
        original_duration = original_schedule.get("project_duration", 0)
        delayed_duration = delayed_schedule.get("project_duration", 0)
        delay_days = delayed_duration - original_duration
        
        cost_analysis = self.compute_cost(delay_days, contract_data)
        
        # Additional analysis
        contract_amount = contract_data.get("contract_amount", 0)
        cost_percentage = (cost_analysis["total"] / contract_amount * 100) if contract_amount > 0 else 0
        
        return {
            "original_duration": original_duration,
            "delayed_duration": delayed_duration,
            "delay_days": delay_days,
            "cost_analysis": cost_analysis,
            "cost_percentage": cost_percentage,
            "formatted_cost_percentage": f"{cost_percentage:.2f}%",
            "recommendations": self._generate_cost_recommendations(delay_days, cost_analysis)
        }
    
    def _generate_cost_recommendations(self, delay_days: int, cost_analysis: Dict[str, Any]) -> List[str]:
        """Generate cost-related recommendations."""
        recommendations = []
        
        if delay_days > 30:
            recommendations.append("장기 지연으로 인한 심각한 비용 증가 - 긴급 대응 필요")
        elif delay_days > 14:
            recommendations.append("중기 지연으로 인한 상당한 비용 증가 - 대응 방안 검토 필요")
        elif delay_days > 7:
            recommendations.append("단기 지연으로 인한 비용 증가 - 모니터링 강화 필요")
        
        if cost_analysis["ld"] > cost_analysis["indirect_cost"]:
            recommendations.append("지연손해금이 간접비보다 높음 - 계약 조건 재검토 고려")
        
        if delay_days > 0:
            recommendations.append("지연 원인 분석 및 재발 방지 대책 수립 필요")
            recommendations.append("가속화 방안 검토로 지연 최소화 고려")
        
        return recommendations
    
    def calculate_roi_for_acceleration(self, acceleration_days: int, acceleration_cost: float, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ROI for project acceleration."""
        if acceleration_days <= 0 or acceleration_cost <= 0:
            return {
                "roi": 0,
                "savings": 0,
                "net_benefit": -acceleration_cost,
                "recommendation": "가속화 불필요"
            }
        
        # Calculate savings from avoiding delays
        ld_rate = contract_data.get("ld_rate", 0.0005)
        contract_amount = contract_data.get("contract_amount", 0)
        indirect_cost_per_day = contract_data.get("indirect_cost_per_day", 0)
        
        savings_per_day = (contract_amount * ld_rate) + indirect_cost_per_day
        total_savings = acceleration_days * savings_per_day
        
        # Calculate ROI
        roi = ((total_savings - acceleration_cost) / acceleration_cost * 100) if acceleration_cost > 0 else 0
        net_benefit = total_savings - acceleration_cost
        
        recommendation = "가속화 추천" if roi > 0 else "가속화 비추천"
        
        return {
            "roi": roi,
            "savings": total_savings,
            "acceleration_cost": acceleration_cost,
            "net_benefit": net_benefit,
            "recommendation": recommendation,
            "formatted": {
                "roi": f"{roi:.1f}%",
                "savings": format_currency(total_savings),
                "acceleration_cost": format_currency(acceleration_cost),
                "net_benefit": format_currency(net_benefit)
            }
        }
