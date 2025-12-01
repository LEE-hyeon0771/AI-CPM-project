"""
Weather service for construction project planning.

기본적으로는 계절/통계 기반 stub 데이터를 사용하지만,
환경설정에 따라 기상청(동네예보, API Hub) 데이터를 조회하여
실제 단기예보를 CPM 분석에 반영할 수 있습니다.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta, timezone
from collections import defaultdict
from statistics import mean
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
            location: Location for forecast (현재는 서울 기준 격자 좌표 사용)

        Returns:
            Weather forecast data in internal unified format.
        """
        # stub 모드이거나 KMA API 키가 없으면 기존 통계 기반 예보 사용
        if self.settings.use_stub or not self.settings.kma_api_key:
            print(f"[WeatherService] Using STUB forecast: {start_date} ~ {end_date}, location={location}")
            return self._get_stub_forecast(start_date, end_date, location)

        try:
            print(f"[WeatherService] Using KMA forecast: {start_date} ~ {end_date}, location={location}")
            return self._call_kma_vilage_api(start_date, end_date, location)
        except Exception as e:
            # 외부 API 오류 시에도 분석 전체가 죽지 않도록 stub 으로 fallback
            print(f"KMA API error, falling back to stub forecast: {e}")
            return self._get_stub_forecast(start_date, end_date, location)
    
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
    
    # ------------------------------------------------------------------
    # KMA 동네예보(VilageFcst) 연동
    # ------------------------------------------------------------------
    @staticmethod
    def _now_kst() -> datetime:
        return datetime.now(timezone.utc) + timedelta(hours=9)

    def _get_base_datetime_short(self) -> (str, str):
        """단기예보용 base_date, base_time 계산 (02, 05, 08, 11, 14, 17, 20, 23시)."""
        kst = self._now_kst() - timedelta(hours=1)
        base_hours = [2, 5, 8, 11, 14, 17, 20, 23]
        date_obj = kst.date()
        hour = kst.hour

        selected_hour = None
        for h in reversed(base_hours):
            if hour >= h:
                selected_hour = h
                break
        if selected_hour is None:  # 0~1시 구간
            selected_hour = 23
            date_obj = date_obj - timedelta(days=1)

        base_date = date_obj.strftime("%Y%m%d")
        base_time = f"{selected_hour:02d}00"
        return base_date, base_time

    def _fetch_short_raw(self, nx: int, ny: int) -> Dict[str, Any]:
        """기상청 API Hub 단기예보(raw JSON) 조회."""
        base_date, base_time = self._get_base_datetime_short()

        base_url = self.settings.kma_endpoint
        if not base_url or base_url.startswith("<"):
            base_url = "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0"

        params = {
            "pageNo": 1,
            "numOfRows": 1000,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx,
            "ny": ny,
            "authKey": self.settings.kma_api_key,
        }

        url = f"{base_url}/getVilageFcst"
        resp = requests.get(url, params=params, timeout=10)
        print(f"[WeatherService] KMA getVilageFcst URL: {resp.url}")
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _group_by_datetime(items: List[Dict[str, Any]]) -> Dict[tuple, Dict[str, Any]]:
        """fcstDate, fcstTime 기준으로 한 시각의 category들을 묶는다."""
        grouped: Dict[tuple, Dict[str, Any]] = defaultdict(dict)
        for it in items:
            date_str = it.get("fcstDate")
            time_str = it.get("fcstTime")
            cat = it.get("category")
            val = it.get("fcstValue")
            if not (date_str and time_str and cat):
                continue
            key = (date_str, time_str)
            grouped[key][cat] = val
        return grouped

    def _call_kma_vilage_api(self, start_date: date, end_date: date, location: str) -> Dict[str, Any]:
        """
        KMA 동네예보 단기예보(getVilageFcst)를 조회하여
        프로젝트 내부에서 사용하는 일 단위 forecast 포맷으로 변환한다.

        - 현재는 격자(nx, ny) = (60, 127)을 서울 기준으로 사용한다.
        - API가 제공하는 예보 범위(약 3일)를 벗어나는 날짜는 stub 데이터로 채운다.
        """
        # 위치 → 격자 좌표 매핑 (필요 시 확장 가능)
        nx, ny = 60, 127  # 서울 종로구 인근 기본값

        raw = self._fetch_short_raw(nx, ny)
        body = raw.get("response", {}).get("body", {})
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]

        grouped = self._group_by_datetime(items)

        # 날짜별로 집계
        per_day: Dict[date, Dict[str, List[float]]] = defaultdict(
            lambda: {"temps": [], "pops": [], "rehs": [], "wsds": [], "skies": [], "ptys": []}
        )

        for (date_str, _time_str), cats in grouped.items():
            try:
                d = date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))
            except Exception:
                continue

            if d < start_date or d > end_date:
                continue

            bucket = per_day[d]

            tmp = cats.get("TMP")
            if tmp is not None:
                try:
                    bucket["temps"].append(float(tmp))
                except ValueError:
                    pass

            pop = cats.get("POP")
            if pop is not None:
                try:
                    bucket["pops"].append(float(pop))
                except ValueError:
                    pass

            reh = cats.get("REH")
            if reh is not None:
                try:
                    bucket["rehs"].append(float(reh))
                except ValueError:
                    pass

            wsd = cats.get("WSD")
            if wsd is not None:
                try:
                    bucket["wsds"].append(float(wsd))
                except ValueError:
                    pass

            sky = cats.get("SKY")
            if sky is not None:
                bucket["skies"].append(str(sky))

            pty = cats.get("PTY")
            if pty is not None:
                bucket["ptys"].append(str(pty))

        # per_day 가 비어 있으면 전체를 stub 으로 대체
        if not per_day:
            return self._get_stub_forecast(start_date, end_date, location)

        forecast_days: List[Dict[str, Any]] = []
        current_date = start_date
        while current_date <= end_date:
            if current_date in per_day:
                bucket = per_day[current_date]
                temps = bucket["temps"] or [15.0]
                min_temp = min(temps)
                max_temp = max(temps)
                avg_temp = mean(temps)

                # condition 결정: 강수형태 우선, 없으면 하늘상태
                condition = "clear"
                ptys = bucket["ptys"]
                skies = bucket["skies"]

                if any(code in ("1", "2", "4") for code in ptys):
                    condition = "rain"
                elif any(code == "3" for code in ptys):
                    condition = "snow"
                else:
                    if any(code == "4" for code in skies):
                        condition = "cloudy"
                    elif any(code == "3" for code in skies):
                        condition = "partly_cloudy"
                    else:
                        condition = "clear"

                pops = bucket["pops"] or [0.0]
                rehs = bucket["rehs"] or [60.0]
                wsds = bucket["wsds"] or [3.0]

                rain_prob = max(pops) / 100.0  # 0.0 ~ 1.0
                humidity = int(mean(rehs))
                wind_speed = max(wsds)

                construction_suitable = self._is_construction_suitable(
                    "rain" if rain_prob > 0.4 else condition, wind_speed, avg_temp
                )

                forecast_days.append(
                    {
                        "date": current_date.isoformat(),
                        "temperature": {"min": min_temp, "max": max_temp, "avg": avg_temp},
                        "condition": condition,
                        "rain_probability": rain_prob,
                        "wind_speed": wind_speed,
                        "humidity": humidity,
                        "construction_suitable": construction_suitable,
                    }
                )
            else:
                # 요청 범위 내인데 단기예보가 커버하지 못하는 날짜는 stub 로 채움
                forecast_days.append(self._generate_stub_day_data(current_date))

            current_date += timedelta(days=1)

        return {
            "location": location,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": forecast_days,
        }
    
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
