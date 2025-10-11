"""
Weather service for construction project planning.
Uses placeholder endpoints with stub data.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import requests
from ...config import get_settings


class WeatherService:
    """Weather service for construction planning."""
    
    def __init__(self):
        self.settings = get_settings()
        self.forecast_cache: Dict[str, Any] = {}
    
    def get_weather_forecast(self, start_date: date, end_date: date, location: str = "서울") -> Dict[str, Any]:
        """
        Get weather forecast for date range.
        
        Args:
            start_date: Start date for forecast
            end_date: End date for forecast
            location: Location for forecast
            
        Returns:
            Weather forecast data
        """
        if self.settings.use_stub:
            return self._get_stub_forecast(start_date, end_date, location)
        
        # Real API call (placeholder)
        return self._call_kma_api(start_date, end_date, location)
    
    def _get_stub_forecast(self, start_date: date, end_date: date, location: str) -> Dict[str, Any]:
        """Generate stub weather forecast data."""
        forecast = {
            "location": location,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": []
        }
        
        current_date = start_date
        while current_date <= end_date:
            # Generate deterministic stub data based on date
            day_data = self._generate_stub_day_data(current_date)
            forecast["days"].append(day_data)
            current_date += timedelta(days=1)
        
        return forecast
    
    def _generate_stub_day_data(self, date: date) -> Dict[str, Any]:
        """Generate stub data for a single day."""
        # Use date to create deterministic but varied data
        day_of_year = date.timetuple().tm_yday
        
        # Simulate seasonal patterns
        if 3 <= date.month <= 5:  # Spring
            base_temp = 15
            rain_prob = 0.3
        elif 6 <= date.month <= 8:  # Summer
            base_temp = 25
            rain_prob = 0.5
        elif 9 <= date.month <= 11:  # Fall
            base_temp = 18
            rain_prob = 0.4
        else:  # Winter
            base_temp = 5
            rain_prob = 0.2
        
        # Add some variation based on day
        temp_variation = (day_of_year % 7) - 3
        temp = base_temp + temp_variation
        
        # Determine weather conditions
        if rain_prob > 0.4:
            condition = "rain"
            wind_speed = 8 + (day_of_year % 5)
        elif temp < 0:
            condition = "snow"
            wind_speed = 5 + (day_of_year % 3)
        else:
            condition = "clear"
            wind_speed = 3 + (day_of_year % 4)
        
        return {
            "date": date.isoformat(),
            "temperature": {
                "min": temp - 5,
                "max": temp + 5,
                "avg": temp
            },
            "condition": condition,
            "rain_probability": rain_prob,
            "wind_speed": wind_speed,
            "humidity": 60 + (day_of_year % 20),
            "construction_suitable": self._is_construction_suitable(condition, wind_speed, temp)
        }
    
    def _is_construction_suitable(self, condition: str, wind_speed: float, temp: float) -> bool:
        """Determine if weather is suitable for construction."""
        if condition in ["rain", "snow"]:
            return False
        if wind_speed > 10:  # High wind
            return False
        if temp < -5 or temp > 35:  # Extreme temperatures
            return False
        return True
    
    def _call_kma_api(self, start_date: date, end_date: date, location: str) -> Dict[str, Any]:
        """Call KMA API (placeholder implementation)."""
        # This would be the real API call
        # For now, return stub data
        return self._get_stub_forecast(start_date, end_date, location)
    
    def get_construction_impact(self, forecast: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze weather impact on construction activities."""
        impact = {
            "total_days": len(forecast["days"]),
            "suitable_days": 0,
            "unsuitable_days": 0,
            "delays": [],
            "recommendations": []
        }
        
        for day in forecast["days"]:
            if day["construction_suitable"]:
                impact["suitable_days"] += 1
            else:
                impact["unsuitable_days"] += 1
                impact["delays"].append({
                    "date": day["date"],
                    "reason": self._get_delay_reason(day),
                    "condition": day["condition"]
                })
        
        # Generate recommendations
        if impact["unsuitable_days"] > 0:
            impact["recommendations"].append("Consider indoor activities during unsuitable weather")
            impact["recommendations"].append("Plan buffer time for weather delays")
        
        return impact
    
    def _get_delay_reason(self, day_data: Dict[str, Any]) -> str:
        """Get reason for construction delay."""
        if day_data["condition"] == "rain":
            return "강우로 인한 작업 중지"
        elif day_data["condition"] == "snow":
            return "강설로 인한 작업 중지"
        elif day_data["wind_speed"] > 10:
            return f"강풍({day_data['wind_speed']}m/s)으로 인한 작업 중지"
        elif day_data["temperature"]["avg"] < -5:
            return "저온으로 인한 작업 중지"
        elif day_data["temperature"]["avg"] > 35:
            return "고온으로 인한 작업 중지"
        else:
            return "기상 조건 불량"
