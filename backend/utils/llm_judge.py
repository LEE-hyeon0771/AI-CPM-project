"""
LLM-as-Judge utilities.

This module provides helper functions to ask an LLM to evaluate
the correctness of CPM/weather/holiday delay logic.
"""

from typing import Any, Dict, List

from .llm_client import get_llm_client


def build_cpm_judge_prompt(
    business_rules: str,
    code_snippet: str,
    scenario_inputs: Dict[str, Any],
    scenario_outputs: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Build messages for LLM-as-judge evaluation of CPM weather/holiday logic.

    Args:
        business_rules: Natural language description of the intended logic.
        code_snippet: Relevant Python code implementing the logic.
        scenario_inputs: Concrete input data used for this run
            (e.g. start_date, project_duration, weather_forecast, holidays).
        scenario_outputs: Actual outputs from the code under test
            (e.g. total_delay_days, holiday_delays, weather_delays, etc.).

    Returns:
        messages list for OpenAI ChatCompletion.
    """

    system_prompt = (
        "당신은 시공 공정표/CPM 및 소프트웨어 품질에 능숙한 시니어 백엔드 엔지니어이자 "
        "코드 리뷰어입니다. 당신의 역할은 **심판(judge)** 으로서, 사람이 정의한 "
        "비즈니스 규칙을 기준으로 코드 결과가 논리적으로 옳은지 평가하는 것입니다. "
        "코드를 직접 수정하지 말고, 규칙과 코드, 입력/출력을 비교 분석하여 "
        "논리적 일관성과 오류 가능성을 평가해 주세요."
    )

    user_content = [
        "다음은 내가 원하는 CPM 지연 계산 규칙과 실제 실행 결과입니다.",
        "",
        "### [1] 비즈니스/도메인 규칙",
        business_rules,
        "",
        "### [2] 실제 Python 코드 구현 (발췌)",
        "```python",
        code_snippet,
        "```",
        "",
        "### [3] 이번 평가에 사용된 입력 데이터 (scenario_inputs)",
        repr(scenario_inputs),
        "",
        "#### 3-1. 캘린더/비근무일 관련 사실 (calendar_facts)",
        "- scenario_inputs 안에 'calendar_facts' 키가 있을 경우, 그 값은 Python datetime 모듈로 미리 계산한 결과입니다.",
        "- 예: 전체 날짜 범위, weekend_dates(토/일), non_working_dates, 그 개수 등.",
        "- 이 값들은 **이미 신뢰할 수 있는 '사실(facts)'이므로, 당신이 달력을 다시 세거나 수정해서는 안 됩니다.**",
        "",
        "### [4] 코드가 실제로 반환한 결과 (scenario_outputs)",
        repr(scenario_outputs),
        "",
        "요청:",
        "아래 7개 섹션 제목과 순서를 **그대로 유지**하여 한국어로 답변해 주세요. "
        "비전공 교수도 이해할 수 있도록, 수식은 최소화하고 직관적인 설명 위주로 작성합니다.",
        "",
        "### 1. 전체 개념 요약",
        "- 이 시나리오에서 공기 지연을 어떻게 해석하는지, "
        "  특히 '비근무일의 기상 악화도 전체 일정 위험을 높이는가?' 관점에서 "
        "  3~6문장 정도로 개념을 정리해 주세요.",
        "- 기상 악화가 직접 작업일이 아니어도 장비 점검, 자재 이동, 후속 공정 순서 등에 "
        "  어떤 간접 영향을 줄 수 있는지도 간단히 언급해 주세요.",
        "",
        "### 2. 수학적 계산 단계",
        "1. **캘린더 관련 값은 재계산하지 마세요.** weekend_dates, non_working_dates, "
        "   holiday_impact['non_working_days'], holiday_impact['holidays'] 등 이미 제공된 값들을 "
        "   그대로 신뢰하고 사용해야 합니다. 본인의 달력 지식으로 주말/공휴일을 다시 세지 마세요.",
        "2. [1]의 규칙과 [3]/[4] 안의 숫자·집합(facts)만을 이용해서, "
        "   holiday_delays, weather_delays, total_delay_days, new_project_duration 이 "
        "   **수학적으로 어떻게 계산되어야 하는지**를 단계별로 보여 주세요.",
        "3. 각 단계마다 어떤 값을 사용했는지 (예: non_working_days, holiday_count, bad_weather_dates 크기 등) "
        "   함께 명시해 주세요.",
        "",
        "### 3. 코드 결과와 계산 결과 비교",
        "- 표 형식으로 다음 네 항목(total_delay_days, holiday_delays, weather_delays, new_project_duration)에 대해 "
        "  '코드 결과 / 규칙 기반 계산 결과 / 일치 여부' 를 한 줄씩 정리해 주세요.",
        "",
        "### 4. 불일치 설명",
        "- 만약 어떤 항목이라도 불일치가 있다면, 어떤 수식 또는 단계에서 차이가 생기는지, "
        "  그리고 그 차이가 가지는 의미(예: 주말 처리, 기상 악화 해석 차이 등)를 설명해 주세요.",
        "- 이번 시나리오에서 모두 일치한다면, '모든 항목이 규칙과 일치한다'고 명시해 주세요.",
        "",
        "### 5. 반복적으로 나타날 수 있는 시나리오",
        "- 이 로직이 특히 잘 드러나는 대표 시나리오 1~2가지를 제시해 주세요 "
        "  (예: 비근무일에만 기상 악화가 몰려 있는 경우, 연속된 악천후 기간 등).",
        "",
        "### 6. 전반적인 판정",
        "- 한 문장으로, 이 코드 로직이 규칙과 현실적인 공정관리 관점에서 전반적으로 "
        "  올바른지/아닌지를 판정해 주세요.",
        "",
        "### 7. 정확도 점수",
        "- 형식: '**점수: X점**' (0~10점, 0점=완전히 잘못됨, 10점=규칙과 완전히 일치).",
        "- 다음 줄에 '- 이유: ...' 형식으로 한 문장 이유를 적어 주세요. "
        "  비전공 교수도 이해할 수 있도록, 너무 기술적인 용어는 피하고 간단한 한국어로 설명해 주세요.",
    ]

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(user_content)},
    ]


def run_cpm_llm_judge(
    business_rules: str,
    code_snippet: str,
    scenario_inputs: Dict[str, Any],
    scenario_outputs: Dict[str, Any],
    temperature: float = 0.0,
    max_tokens: int = 1200,
) -> str:
    """
    Call LLM-as-judge for a single CPM scenario.

    This is a thin wrapper around `LLMClient.chat_completion`.
    """
    llm = get_llm_client()
    messages = build_cpm_judge_prompt(
        business_rules=business_rules,
        code_snippet=code_snippet,
        scenario_inputs=scenario_inputs,
        scenario_outputs=scenario_outputs,
    )
    return llm.chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )



