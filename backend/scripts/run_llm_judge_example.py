"""
Example script: run LLM-as-judge on CPM weather/holiday delay logic.

사용법 (venv 활성화 후 프로젝트 루트에서):
    python -m backend.scripts.run_llm_judge_example

콘솔에 사람 읽기 좋은 리포트를 출력하고,
동시에 CSV 파일(llm_judge_results.csv)로 핵심 지표를 저장한다.
"""

import csv
import os
import re
from datetime import date, timedelta
from typing import Any, Dict

from ..agents.cpm_weather_cost import CPMWeatherCostAgent  # type: ignore
from ..utils.llm_judge import run_cpm_llm_judge


def build_business_rules() -> str:
    """Return natural language description of intended CPM rules."""
    return (
        "- 프로젝트 기간: 시작일 start_date 기준으로 project_duration일 동안 진행한다.\n"
        "- 공휴일/주말 지연 (holiday_delays):\n"
        "  - 전체 공사 기간(start_date ~ end_date) 캘린더를 기준으로,\n"
        "    토/일 + 법정 공휴일을 비근무일(주말+공휴일)로 본다.\n"
        "  - 어떤 종료일 end_date 를 가정했을 때, 그 구간의 비근무일(주말+공휴일) 개수를\n"
        "    holiday_delays 라고 정의한다.\n"
        "- 날씨 지연 (weather_delays, 위험 기반 해석):\n"
        "  - weather_forecast['days'] 중 construction_suitable == False 인 날짜를 기상 불량일로 본다.\n"
        "  - 기상 불량일은 그날 작업 여부와 상관 없이, 장비 점검·자재 이동·후속 공정 순서 등에\n"
        "    간접적인 영향을 주어 전체 일정 여유(buffer)를 줄이는 '위험일'로 간주한다.\n"
        "  - 따라서 주말/공휴일(비근무일)에 발생한 기상 불량도 weather_delays에 포함한다.\n"
        "  - weather_delays = 기상 불량일 개수 (bad_weather_dates의 크기).\n"
        "- 최종 지연(중복 조정 + self-consistent 모델):\n"
        "  - weather_overlap_nonworking = '기상 불량일' ∩ '비근무일(주말+공휴일)'의 날짜 수.\n"
        "  - 어떤 end_date 를 가정하면,\n"
        "      total_delay_days(end_date) = holiday_delays(end_date) + weather_delays − weather_overlap_nonworking(end_date)\n"
        "      new_project_duration(end_date) = project_duration + total_delay_days(end_date)\n"
        "  - self-consistent 한 종료일 end* 는 다음 조건을 만족하도록 반복(while-loop)으로 찾는다.\n"
        "      end* = start_date + new_project_duration(end*) − 1\n"
        "  - 최종적으로, total_delay_days = total_delay_days(end*) 이며\n"
        "    new_project_duration = project_duration + total_delay_days 로 정의한다.\n"
    )


def build_scenario_inputs() -> Dict[str, Any]:
    """
    Build a simple scenario for evaluation.

    실제 서비스와 완전히 동일할 필요는 없고,
    시작일 / 기간 / weather_forecast 형태만 맞춰주면 된다.
    """
    start_date = date(2025, 12, 4)
    project_duration = 25

    # 예시용 간단 weather_forecast (실제 서비스에서는 WeatherService 결과를 사용)
    weather_forecast = {
        "days": [
            {"date": "2025-12-06", "construction_suitable": False, "condition": "강풍"},
        ]
    }

    return {
        "start_date": start_date.isoformat(),
        "project_duration": project_duration,
        "weather_forecast": weather_forecast,
    }


def build_calendar_facts(start_date_str: str, project_duration: int) -> Dict[str, Any]:
    """
    Python datetime 으로 미리 계산한 캘린더/비근무일 정보.

    LLM judge 는 이 값을 '사실(facts)'로 신뢰하고, 달력을 다시 세지 말아야 한다.
    """
    start = date.fromisoformat(start_date_str)
    end = start + timedelta(days=project_duration - 1)

    weekend_dates = []
    current = start
    while current <= end:
        if current.weekday() >= 5:  # 토(5), 일(6)
            weekend_dates.append(current.isoformat())
        current += timedelta(days=1)

    return {
        "calendar_range": [start.isoformat(), end.isoformat()],
        "weekend_dates": weekend_dates,
        "weekend_count": len(weekend_dates),
        # 필요하면 향후 holidays, non_working_dates 등을 여기에 추가할 수 있다.
    }


def run_code_under_test(scenario_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the CPMWeatherCostAgent (or equivalent) to get actual outputs.

    필요에 따라 이 부분을 프로젝트 구조에 맞게 수정해서 사용하면 된다.
    """
    agent = CPMWeatherCostAgent()

    # 실제 에이전트 인터페이스에 맞게 호출
    # 여기서는 내부 지연 시뮬레이션 메서드(_simulate_delays)를 직접 사용한다.
    start_date = date.fromisoformat(scenario_inputs["start_date"])
    project_duration = scenario_inputs["project_duration"]
    weather_forecast = scenario_inputs["weather_forecast"]

    # ideal_schedule 은 최소한 project_duration 만 있으면 된다.
    dummy_ideal_schedule: Dict[str, Any] = {
        "project_duration": project_duration,
        "tasks": [],
        "critical_path": [],
    }

    # CPMWeatherCostAgent 내부 구현에 맞춰, 지연 분석 부분만 직접 호출
    delay_analysis = agent._simulate_delays(  # type: ignore[attr-defined]
        ideal_schedule=dummy_ideal_schedule,
        wbs_items=[],
        start_date=start_date,
        forecast_start_date=None,
        forecast_duration_days=None,
    )

    return delay_analysis


def parse_judge_report(judge_report: str) -> Dict[str, Any]:
    """
    LLM judge의 텍스트 리포트에서 점수와 한 줄 요약(이유)을 파싱한다.

    형식 가정 (예):
    **점수: 3/10**
    - 이유: ...
    """
    score = None
    reason = ""

    for raw_line in judge_report.splitlines():
        line = raw_line.strip()
        # 마크다운 bold(**) 제거
        if line.startswith("**") and line.endswith("**"):
            line = line.strip("*").strip()

        if "점수" in line:
            m = re.search(r"점수[:：]\s*(\d+)\s*/\s*10", line)
            if m:
                try:
                    score = int(m.group(1))
                except ValueError:
                    score = None
        elif "이유:" in line and not reason:
            # "- 이유: ..." 또는 "이유: ..." 형태 처리
            reason_part = line
            reason_part = reason_part.lstrip("-").strip()
            reason = reason_part.split("이유:", 1)[-1].strip()

    return {
        "judge_score": score,
        "judge_reason": reason,
    }


def write_csv_row(
    filepath: str,
    scenario_inputs: Dict[str, Any],
    scenario_outputs: Dict[str, Any],
    judge_report: str,
) -> None:
    """LLM judge 결과를 CSV 한 줄로 저장한다."""
    calendar_facts = scenario_inputs.get("calendar_facts", {})

    parsed = parse_judge_report(judge_report)

    row = {
        "scenario_id": 1,  # 필요하면 나중에 여러 시나리오를 돌릴 때 변경
        "start_date": scenario_inputs.get("start_date"),
        "project_duration": scenario_inputs.get("project_duration"),
        "calendar_start": (calendar_facts.get("calendar_range") or ["", ""])[0],
        "calendar_end": (calendar_facts.get("calendar_range") or ["", ""])[1],
        "weekend_count": calendar_facts.get("weekend_count"),
        "weekend_dates": ",".join(calendar_facts.get("weekend_dates", [])),
        "total_delay_days_code": scenario_outputs.get("total_delay_days"),
        "holiday_delays_code": scenario_outputs.get("holiday_delays"),
        "weather_delays_code": scenario_outputs.get("weather_delays"),
        "new_project_duration_code": scenario_outputs.get("new_project_duration"),
        "judge_score": parsed.get("judge_score"),
        "judge_reason": parsed.get("judge_reason"),
        "judge_report_raw": judge_report.replace("\n", "\\n"),
    }

    fieldnames = list(row.keys())
    file_exists = os.path.exists(filepath)

    with open(filepath, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    business_rules = build_business_rules()
    scenario_inputs = build_scenario_inputs()

    # 캘린더/비근무일 facts 를 미리 계산해서 scenario_inputs 에 넣어준다.
    scenario_inputs["calendar_facts"] = build_calendar_facts(
        scenario_inputs["start_date"],
        scenario_inputs["project_duration"],
    )

    scenario_outputs = run_code_under_test(scenario_inputs)

    # 관심 있는 코드 부분만 문자열로 발췌해서 붙여 넣는다.
    # 필요하면 실제 파일에서 복사해서 이 문자열을 갱신해 주면 된다.
    code_snippet = """
        # cpm_weather_cost.CPMWeatherCostAgent._simulate_delays 중 일부
        weather_impact = self.weather_service.get_construction_impact(weather_forecast)

        calendar_policy = "5d"
        full_project_end = start_date + timedelta(days=project_duration - 1) if project_duration > 0 else start_date
        holiday_impact = self.holiday_service.get_holiday_impact(start_date, full_project_end, calendar_policy)

        # 1) 기상 불량일 집합 (예보 창에 한정)
        bad_weather_dates = {
            date.fromisoformat(day["date"])
            for day in weather_forecast["days"]
            if not day["construction_suitable"]
        }

        # 2) 반복/수렴형 종료일 계산
        calendar_policy = "5d"
        if project_duration > 0:
            end_date = start_date + timedelta(days=project_duration - 1)
        else:
            end_date = start_date

        max_iterations = 10
        weather_total_bad_days = len(bad_weather_dates)
        weather_overlap_nonworking = 0
        weather_delays = weather_total_bad_days
        holiday_delays = 0
        total_delays = 0

        for _ in range(max_iterations):
            full_project_end = end_date

            # (1) 공휴일/주말 영향
            holiday_impact = self.holiday_service.get_holiday_impact(start_date, full_project_end, calendar_policy)

            # (2) 비근무일(주말+공휴일) 집합
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

            # (3) 요약 지표
            weather_total_bad_days = len(bad_weather_dates)
            weather_overlap_nonworking = len(bad_weather_dates & non_working_dates)
            weather_delays = weather_total_bad_days
            holiday_delays = holiday_impact["non_working_days"]

            total_delays = holiday_delays + weather_delays - weather_overlap_nonworking
            new_project_duration = project_duration + total_delays
            new_end_date = start_date + timedelta(days=new_project_duration - 1) if new_project_duration > 0 else start_date

            if new_end_date == end_date:
                break
            end_date = new_end_date
    """

    judge_report = run_cpm_llm_judge(
        business_rules=business_rules,
        code_snippet=code_snippet,
        scenario_inputs=scenario_inputs,
        scenario_outputs=scenario_outputs,
    )

    print("=== LLM Judge Report ===")
    print(judge_report)

    # CSV 파일로도 결과 저장
    txt_path = os.path.join(os.path.dirname(__file__), "llm_judge_results.txt")
    write_csv_row(txt_path, scenario_inputs, scenario_outputs, judge_report)
    print(f"\nCSV 저장 완료: {txt_path}")


if __name__ == "__main__":
    main()


