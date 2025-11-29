"""
Holiday service for construction project planning.
Uses placeholder endpoints with stub data.
"""
from typing import Dict, Any, List, Set
from datetime import datetime, date, timedelta
import requests
from ...config import get_settings


class HolidayService:
    """Holiday service for construction planning."""
    
    def __init__(self):
        self.settings = get_settings()
        self.holiday_cache: Dict[int, Set[date]] = {}  # year -> set of dates
    
    def get_holidays(self, year: int) -> Set[date]:
        """
        Get holidays for a specific year.
        
        Args:
            year: Year to get holidays for
            
        Returns:
            Set of holiday dates
        """
        if year in self.holiday_cache:
            return self.holiday_cache[year]
        
        if self.settings.use_stub:
            holidays = self._get_stub_holidays(year)
        else:
            holidays = self._call_holiday_api(year)
        
        self.holiday_cache[year] = holidays
        return holidays
    
    def _get_stub_holidays(self, year: int) -> Set[date]:
        """Generate stub holiday data."""
        holidays = set()
        
        # Fixed holidays
        fixed_holidays = [
            (1, 1),   # New Year's Day
            (3, 1),   # Independence Movement Day
            (5, 5),   # Children's Day
            (6, 6),   # Memorial Day
            (8, 15),  # Liberation Day
            (10, 3),  # National Foundation Day
            (10, 9),  # Hangeul Day
            (12, 25)  # Christmas Day
        ]
        
        for month, day in fixed_holidays:
            try:
                holiday_date = date(year, month, day)
                holidays.add(holiday_date)
            except ValueError:
                pass  # Invalid date
        
        # Lunar holidays (simplified - using fixed dates for stub)
        lunar_holidays = [
            (1, 28),  # Lunar New Year (simplified)
            (1, 29),  # Lunar New Year (simplified)
            (1, 30),  # Lunar New Year (simplified)
            (4, 8),   # Buddha's Birthday (simplified)
            (8, 14),  # Chuseok (simplified)
            (8, 15),  # Chuseok (simplified)
            (8, 16)   # Chuseok (simplified)
        ]
        
        for month, day in lunar_holidays:
            try:
                holiday_date = date(year, month, day)
                holidays.add(holiday_date)
            except ValueError:
                pass
        
        # Add some random holidays for variety
        import random
        random.seed(year)  # Deterministic randomness
        
        for _ in range(3):
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            try:
                holiday_date = date(year, month, day)
                if holiday_date not in holidays:
                    holidays.add(holiday_date)
            except ValueError:
                pass
        
        return holidays
    
    def _call_holiday_api(self, year: int) -> Set[date]:
        """Call external holiday API (정부 공휴일 API 또는 통합 캘린더 API).

        CALENDAR_ENDPOINT가 설정되어 있으면 그 주소를, 아니면 HOLIDAY_ENDPOINT를 사용합니다.
        실제 정부 API 스펙에 맞게 params와 응답 매핑 부분만 수정해서 쓰면 됩니다.
        """
        base_url = self.settings.calendar_endpoint or self.settings.holiday_endpoint
        if not base_url or base_url.startswith("<"):
            # 설정이 안 되어 있으면 안전하게 스텁으로 fallback
            return self._get_stub_holidays(year)

        params = {
            "type": "holiday",  # 통합 API라면 타입 구분용
            "year": year,
            "api_key": self.settings.holiday_api_key,
        }

        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # data 예시 형태를 {"holidays": ["2025-01-01", ...]} 로 가정
        # 실제 응답 포맷에 맞게 date.fromisoformat(...) 부분만 조정해서 사용하세요.
        holidays: Set[date] = set()
        for d in data.get("holidays", []):
            try:
                holidays.add(date.fromisoformat(d))
            except Exception:
                continue

        return holidays
    
    def is_holiday(self, check_date: date) -> bool:
        """Check if a date is a holiday."""
        holidays = self.get_holidays(check_date.year)
        return check_date in holidays
    
    def get_working_days(self, start_date: date, end_date: date, calendar_policy: str = "5d") -> int:
        """
        Calculate working days between two dates.
        
        Args:
            start_date: Start date
            end_date: End date
            calendar_policy: Calendar policy ("5d", "6d", "7d")
            
        Returns:
            Number of working days
        """
        if calendar_policy == "7d":
            # 7-day work week
            return (end_date - start_date).days + 1
        
        # Get holidays for the year range
        holidays = set()
        for year in range(start_date.year, end_date.year + 1):
            holidays.update(self.get_holidays(year))
        
        working_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            if calendar_policy == "5d":
                # 5-day work week (Monday-Friday)
                if current_date.weekday() < 5 and current_date not in holidays:
                    working_days += 1
            elif calendar_policy == "6d":
                # 6-day work week (Monday-Saturday)
                if current_date.weekday() < 6 and current_date not in holidays:
                    working_days += 1
            
            current_date += timedelta(days=1)
        
        return working_days
    
    def get_next_working_day(self, from_date: date, calendar_policy: str = "5d") -> date:
        """Get the next working day from a given date."""
        current_date = from_date + timedelta(days=1)
        
        while True:
            if calendar_policy == "5d":
                if current_date.weekday() < 5 and not self.is_holiday(current_date):
                    return current_date
            elif calendar_policy == "6d":
                if current_date.weekday() < 6 and not self.is_holiday(current_date):
                    return current_date
            elif calendar_policy == "7d":
                if not self.is_holiday(current_date):
                    return current_date
            
            current_date += timedelta(days=1)
    
    def get_holiday_impact(self, start_date: date, end_date: date, calendar_policy: str = "5d") -> Dict[str, Any]:
        """Analyze holiday impact on construction schedule."""
        total_days = (end_date - start_date).days + 1
        working_days = self.get_working_days(start_date, end_date, calendar_policy)
        non_working_days = total_days - working_days
        
        # Get holidays in the range
        holidays = set()
        for year in range(start_date.year, end_date.year + 1):
            holidays.update(self.get_holidays(year))
        
        holiday_dates = [d for d in holidays if start_date <= d <= end_date]
        
        return {
            "total_days": total_days,
            "working_days": working_days,
            "non_working_days": non_working_days,
            "holidays": [d.isoformat() for d in holiday_dates],
            "holiday_count": len(holiday_dates),
            "calendar_policy": calendar_policy
        }
