## Smart Construction Scheduling & Economic Analysis

AI를 활용하여 **건설 공사 WBS·일정·기상·법규 정보를 통합 분석**하는 멀티 에이전트 기반 시스템입니다.  
자연어로 질의하면, CPM 기반 이상 일정, 날씨·공휴일에 따른 지연 분석, 건설 안전 규정 요약을 한 번에 제공합니다.

---

### 1. 프로젝트 목적

- **현실적인 공정관리 지원**: 공사 담당자가 자연어로 WBS와 요구사항을 입력하면, CPM 기반 이상 일정과 날씨·공휴일을 반영한 지연을 자동 계산합니다.
- **안전 규정 준수 보조**: KOSHA 등 안전 규정 PDF를 RAG 인덱스로 구축하여, 공사 종류·작업 유형별 안전 기준과 작업중지 기준을 자동으로 찾아 요약합니다.
- **의사결정 품질 향상**: LLM이 각 에이전트 결과를 요약·통합하여, PM/소장 입장에서 바로 활용 가능한 “경영자용 요약(executive summary)”를 생성합니다.
- **연구·논문 활용 가능성**: CPM, RAG, 멀티 에이전트, LLM 프롬프트 엔지니어링을 결합한 아키텍처로, 공정관리·건설 인공지능 분야 논문 실험 플랫폼으로 활용될 수 있습니다.

---

### 2. 프로젝트 의의

- **전통 공정관리 기법과 LLM의 결합**  
  - 기존 CPM·PERT 도구는 정형화된 입력과 전문적인 조작이 필요했습니다.  
  - 본 프로젝트는 자연어 WBS → 구조화 → CPM → 기상·공휴일 시뮬레이션 → 법규 RAG를 **단일 파이프라인**으로 구성하여, 비전문가도 쉽게 활용할 수 있도록 합니다.

- **규정 기반 안전관리의 자동화 가능성 제시**  
  - `law_rag.py` + `threshold_builder.py` + `rules/store.py` 는 안전 규정 문서에서 **풍속, 온도, 강우량, 작업중지 기준 등 수치 규정**을 추출·구조화하는 체인을 제공합니다.
  - 이는 향후 “규정 기반 디지털 트윈” 연구의 핵심 컴포넌트로 확장 가능합니다.

- **에이전트–툴–체인 구조의 실증 예제**  
  - Supervisor–Agents–Tools–RAG–LLM 으로 구성된 구조는 **멀티 에이전트 시스템 설계·검증**에 좋은 레퍼런스가 됩니다.

---

### 3. 전체 아키텍처 (Agent–Tool–Chain)

```text
사용자 (웹/모바일 Flutter UI)
        │
        ▼
Frontend (Flutter, lib/home.dart)
  ├─ /api/chat      → 일정·안전 통합 분석
  └─ /api/rules/... → 규칙 리프레시·조회
        │
        ▼
Backend (FastAPI, backend/app.py)
  ├─ Supervisor (supervisor.py)
  │    └─ LLM 기반 의도 분석 → required_agents 결정
  ├─ Agents (backend/agents/)
  │    ├─ LawRAGAgent (law_rag.py)
  │    ├─ ThresholdBuilderAgent (threshold_builder.py)
  │    ├─ CPMWeatherCostAgent (cpm_weather_cost.py)
  │    └─ MergerAgent (merger.py)
  └─ Tools (backend/tools/services/, rag/, rules/)
       ├─ WBSParser (wbs_parser.py)
       ├─ CPMService (cpm.py)
       ├─ WeatherService (weather.py)
       ├─ HolidayService (holidays.py)
       ├─ RagStoreFaiss (rag/faiss_store.py)
       └─ RulesStore (rules/store.py)

데이터 계층
  ├─ prompts/*.txt        : LLM 프롬프트
  ├─ data/faiss/*.faiss   : 법규 RAG 인덱스
  └─ data/rules/*.jsonl   : 추출된 규칙
```

**Agent–Tool–Chain 흐름 (일반 일정 + 안전 규정 질문)**  
1. `frontend/lib/main.dart` 의 `/api/chat` 호출 → `backend/app.py::chat` 진입  
2. `Supervisor` 가 `message`(자연어 질의)를 분석 → `required_agents` 결정  
3. `WBSParser` 가 `wbs_text` 또는 `message` 에서 WBS를 구조화 (`WBSItem` 리스트)  
4. `LawRAGAgent` 가 `RagStoreFaiss` 를 통해 관련 규정 스니펫을 검색 (`Citation` 리스트)  
5. `ThresholdBuilderAgent` 가 규정에서 수치 임계값을 추출 (`RuleItem` 리스트)  
6. `CPMWeatherCostAgent` 가 WBS + 계약정보 + 날씨·공휴일 정보를 이용해 CPM + 지연 분석 수행  
7. `MergerAgent` 가 위 결과를 통합하고, 필요 시 LLM으로 한국어 요약 카드·테이블을 생성 (`ChatResponse`)  
8. Frontend 가 `ui.tables`, `ui.cards`, `citations` 를 시각화.

**법규 전용 모드 (`mode="law_only"`)**  
`frontend/lib/main2.dart` 에서 `mode: "law_only"` 로 `/api/chat` 을 호출하면,  
`app.py::chat` 이 `required_agents = ["law_rag", "merger"]` 로 강제하여 **CPM 분석 없이** 법규 Q&A만 수행합니다.

---

### 4. 프로젝트 구조 (Project Structure)

```text
AI-CPM-project/
├── backend/
│   ├── app.py                 # FastAPI 엔트리포인트 및 HTTP 엔드포인트
│   ├── config.py              # 환경설정 로딩 (Settings)
│   ├── supervisor.py          # Supervisor 에이전트 (의도 분석 및 라우팅)
│   ├── schemas/
│   │   └── io.py              # Pydantic 요청/응답 모델 (ChatRequest, ChatResponse 등)
│   ├── agents/
│   │   ├── law_rag.py         # 법규 RAG 에이전트 (LawRAGAgent)
│   │   ├── threshold_builder.py # 규정에서 임계값 추출 (ThresholdBuilderAgent)
│   │   ├── cpm_weather_cost.py  # CPM + 날씨 + 공휴일 분석 (CPMWeatherCostAgent)
│   │   └── merger.py          # 결과 통합·요약 에이전트 (MergerAgent)
│   ├── tools/
│   │   ├── services/
│   │   │   ├── wbs_parser.py  # 자연어 WBS 파서 (규칙 + LLM 하이브리드)
│   │   │   ├── cpm.py         # CPM 계산기 (ES/EF/LS/LF/TF)
│   │   │   ├── weather.py     # WeatherService (KMA/캘린더 API or stub)
│   │   │   ├── holidays.py    # HolidayService (공휴일·근무일 계산)
│   │   │   └── cost.py        # 비용 관련 로직 (확장 포인트)
│   │   ├── rag/
│   │   │   └── faiss_store.py # RagStoreFaiss (FAISS 검색 래퍼)
│   │   └── rules/
│   │       └── store.py       # RulesStore (규칙 jsonl 저장/로드)
│   └── utils/
│       ├── prompt_loader.py   # PromptLoader, get_system_prompt, get_query_prompt
│       └── llm_client.py      # OpenAI 기반 LLMClient 래퍼
│
├── frontend/
│   ├── lib/
│   │   ├── home.dart          # Flutter 진입 화면 (두 기능 선택 메뉴)
│   │   ├── main.dart          # 스마트 건설 일정 분석 화면 (CPM + 날씨 + 규정)
│   │   └── main2.dart         # 건설 안전 규정 Q&A 화면 (법규 전용)
│   ├── pubspec.yaml           # Flutter 의존성 정의
│   └── android/, web/, ...    # Flutter 플랫폼별 빌드 스캐폴드
│
├── prompts/                   # 에이전트별 LLM 프롬프트
│   ├── supervisor_system.txt
│   ├── law_rag_system.txt / law_rag_query.txt
│   ├── threshold_builder_system.txt / threshold_builder_extraction.txt
│   ├── cpm_analysis_system.txt / cpm_analysis_query.txt
│   ├── merger_system.txt / merger_formatting.txt
│   └── wbs_parser_system.txt / wbs_parser_query.txt
│
├── data/
│   ├── faiss/                 # 법규 PDF 임베딩 인덱스 (index.faiss, meta.jsonl)
│   └── rules/                 # 추출된 규칙(rule) jsonl
│
├── tests/                     # pytest 기반 백엔드 테스트
├── env.example.txt            # .env 예시 템플릿
├── requirements.txt           # Python 의존성 목록
└── README.md
```

---

### 5. Backend 실행 방법

#### 5.1 사전 요구 사항

- Python 3.10 이상 (프로젝트는 3.10 기준으로 개발됨)
- 가상환경 사용 권장 (`venv`)
- 선택 사항: OpenAI API 키 (LLM 기능 활성화)

#### 5.2 환경 설정

```bash
cd AI-CPM-project

python -m venv venv
venv\Scripts\activate        # Windows
# 또는
source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

`.env` 파일 생성 및 설정:

```bash
copy env.example.txt .env    # Windows
# cp env.example.txt .env    # macOS / Linux
```

`.env` 주요 항목 (backend/config.py 에서 사용):

- `OPENAI_API_KEY` : LLM 사용 시 필수 (없으면 규칙 기반 fallback)
- `LLM_MODEL`, `*_MODEL` : 각 에이전트별 모델 이름 (기본값은 `gpt-4o-mini`)
- `USE_STUB=true` : 외부 날씨/공휴일 API 대신 stub 데이터 사용 (개발 모드 권장)
- `FAISS_INDEX_PATH`, `FAISS_META_PATH` : 법규 RAG 인덱스 위치

#### 5.3 백엔드 서버 실행

```bash
venv\Scripts\activate
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

- 브라우저에서 `http://localhost:8000/docs` 접속 시 자동 API 문서(Swagger UI)를 확인할 수 있습니다.
- 모바일·다른 PC에서 접근할 때는 `http://<PC_IP>:8000` 형태로 접속합니다.

---

### 6. Frontend 실행 방법 (Flutter Web & Mobile)

#### 6.1 사전 요구 사항

- Flutter SDK (stable 채널)
- Android Studio / Xcode (모바일 빌드 시)
- Chrome 브라우저 (웹 실행 시)

#### 6.2 의존성 설치

```bash
cd AI-CPM-project/frontend
flutter pub get
```

#### 6.3 웹에서 실행 (개발 편의용)

```bash
cd AI-CPM-project/frontend
flutter run -d chrome -t lib/home.dart
```

#### 6.4 모바일 디바이스에서 실행 (예: Android)

1. 휴대폰에서 개발자 모드 + USB 디버깅 활성화 후 PC와 연결  
2. 디바이스 확인:
   ```bash
   flutter devices
   ```
3. 실행:
   ```bash
   flutter run -d <device_id> -t lib/home.dart
   ```

#### 6.5 Backend 주소 설정

모바일 디바이스에서 백엔드에 접속할 때는 `127.0.0.1` 대신 **PC의 IP 주소**를 사용해야 합니다.  
예: PC `ipconfig` 결과가 `IPv4 주소 192.168.0.2` 인 경우:

```dart
// frontend/lib/main.dart
static const String _backendBaseUrl = '<ipconfig wifi>';

// frontend/lib/main2.dart
static const String _backendBaseUrl = '<ipconfig wifi>';
```

PC와 모바일이 같은 Wi‑Fi 에 있고, 윈도우 방화벽에서 8000 포트가 허용되어 있어야 합니다.

---

### 7. 에이전트 및 도구 상세 설명

#### 7.1 Supervisor (`backend/supervisor.py`)

- 역할: 사용자의 한국어 질의를 분석해 어떤 에이전트를 호출할지 결정하는 **의도 라우터**입니다.
- LLM 기반 라우팅:
  - `supervisor_system.txt` 프롬프트와 OpenAI 모델을 사용해 JSON 형식의 라우팅 결과를 생성합니다.
  - 출력: `required_agents`, `analysis_mode`, `forecast_offset_days`, `forecast_duration_days` 등.
- Regex 기반 fallback:
  - LLM이 없을 경우, 미리 정의된 정규식 패턴으로 `law_regulation`, `schedule`, `weather`, `cost` 등의 의도를 감지합니다.

#### 7.2 WBSParser (`backend/tools/services/wbs_parser.py`)

- 입력: `wbs_text` (WBS 라인 형식 또는 완전 자연어 서술)
- 단계:
  1. 규칙 기반 파서로 `A: 작업명, 5일, 선행 없음, 유형 EARTHWORK` 형식을 우선 파싱
  2. 실패 시 LLM(`wbs_parser_query.txt`)을 사용해 JSON 배열 형태의 `WBSItem` 리스트 생성
  3. 마지막으로 간단한 휴리스틱 파서로 자연어 텍스트에서 “작업명 + N일” 패턴을 추출
- 출력: `List[WBSItem]` (id, name, duration, predecessors, work_type)

#### 7.3 LawRAGAgent (`backend/agents/law_rag.py`)

- RAG 파이프라인:
  1. `get_query_prompt("law_rag", ...)` 로 검색 질의 포맷팅
  2. `RagStoreFaiss` 로 FAISS 인덱스에서 k개 스니펫 검색
  3. `Citation` 모델로 정규화 (document, page, snippet, score)
  4. LLM 사용 가능 시, 규정 스니펫을 요약·정제해 더 읽기 쉬운 텍스트 생성
- Fallback 모드:
  - FAISS 인덱스가 없거나 LLM이 비활성화된 경우, 내장된 예시 규정을 기반으로 기본적인 안전 기준을 제공합니다.

#### 7.4 ThresholdBuilderAgent (`backend/agents/threshold_builder.py`)

- LawRAGAgent가 가져온 텍스트에서 **풍속, 온도, 강우량, 작업중지 기준** 등의 수치를 추출합니다.
- 규칙 기반/간단한 패턴 매칭으로 `RuleItem` 리스트를 생성하고, `RulesStore` 에 저장할 수 있습니다.

#### 7.5 CPMWeatherCostAgent (`backend/agents/cpm_weather_cost.py`)

- 입력: `wbs_json`(WBSItem 리스트), `contract_data`, `rules`
- 주요 기능:
  - `CPMService` 를 사용해 **이상 일정(ideal_schedule)** 을 계산 (ES/EF/LS/LF/TF, 임계경로 등)
  - `WeatherService`, `HolidayService` 를 통해 특정 기간의 **날씨 부적합일·공휴일**을 계산
  - 이를 바탕으로 총 지연일, 날씨 지연·공휴일 지연, 지연 일자별 상세 `DelayRow` 리스트를 생성
  - LLM 사용 시, 지연 분석을 바탕으로 일정 단축·리스크 완화에 대한 권장사항을 자연어로 생성

#### 7.6 MergerAgent (`backend/agents/merger.py`)

- 역할: 다양한 에이전트 결과(`law_rag`, `threshold_builder`, `cpm_weather_cost`)를 모아 **단일 `ChatResponse`** 로 합칩니다.
- 구성 요소:
  - `citations`: 법규 RAG 결과 상위 N개
  - `ideal_schedule`, `delay_table`: CPM·지연 분석 결과
  - `ui.tables`: DataTable 렌더링용 표 구조 (`UITable`)
  - `ui.cards`: KPI·요약을 보여주는 카드 구조 (`UICard`)
- LLM 요약:
  - 일정·지연 분석이 있는 경우: “💡 종합 분석” 카드 생성
  - 법규만 있는 경우(`analysis_mode == "law_only"`): “💡 법규 설명” 카드로 법규 요약 생성

#### 7.7 기타 서비스·저장소

- `WeatherService` (`backend/tools/services/weather.py`)  
  - `USE_STUB=true` 일 때는 계절·날짜 기반의 결정적 stub 데이터를 생성합니다.
  - 실제 API를 사용할 수 있도록 `calendar_endpoint` / `kma_endpoint`를 위한 확장 포인트를 제공합니다.

- `HolidayService` (`backend/tools/services/holidays.py`)  
  - 주말·공휴일을 고려한 비근무일 계산 로직을 제공합니다.

- `RulesStore` (`backend/tools/rules/store.py`)  
  - `RuleItem` 리스트를 `data/rules/rules.jsonl` 에 저장/로드하여, 규정 기반 임계값을 재사용할 수 있게 합니다.

---

### 8. LLM-as-Judge 기반 로직 검증

이 프로젝트는 LLM을 “답 생성기”로만 쓰지 않고,  
**CPM + 날씨 + 공휴일 지연 계산 로직 자체를 평가하는 심판(judge)** 로도 활용합니다.

#### 8.1 평가 목적

- **수작업 검증 부담 완화**: 주말/공휴일과 악천후가 복잡하게 겹치는 다양한 시나리오에서  
  사람이 모든 케이스를 직접 계산하기 어렵기 때문에, LLM을 이용해 로직의 타당성을 반복적으로 점검합니다.
- **논문·보고서용 정성 평가**: 비전공자(예: 건설관리 전공 교수)를 대상으로,  
  “현재 지연 계산 로직이 어떤 관점에서 합리적인지/어디가 한계인지”를 **설명형 리포트**로 자동 생성합니다.

#### 8.2 Judge 아키텍처

- `backend/utils/llm_client.py`
  - OpenAI API 래퍼 (`LLMClient`) 로, 전체 에이전트에서 공통으로 사용합니다.
- `backend/utils/llm_judge.py`
  - LLM-as-judge 전용 유틸리티.
  - `build_cpm_judge_prompt(...)`:  
    - 비즈니스 규칙(사람이 정의한 지연 계산 규칙)  
    - 실제 Python 코드 스니펫 (`CPMWeatherCostAgent._simulate_delays` 일부)  
    - 입력 시나리오(`scenario_inputs`)와 코드 출력(`scenario_outputs`)  
    - Python이 미리 계산한 캘린더 facts (`calendar_facts`)  
    를 하나의 심판용 프롬프트로 구성합니다.
  - `run_cpm_llm_judge(...)`: 위 프롬프트를 LLM에 전달해 평가 리포트를 가져오는 함수입니다.
- `backend/scripts/run_llm_judge_example.py`
  - 예시 스크립트. 가상의 CPM·날씨·공휴일 시나리오를 정의하고  
    `CPMWeatherCostAgent._simulate_delays(...)` 로 지연 분석을 수행한 뒤,  
    그 결과를 LLM judge 에 전달하여 **텍스트 리포트 + CSV/텍스트 로그**를 생성합니다.

#### 8.3 평가 기준 (비즈니스 규칙 요약)

Judge 프롬프트에는 사람이 정의한 일정/지연 규칙이 자연어로 주입됩니다. 핵심은 다음과 같습니다.

- **공사 기간**
  - `start_date` 기준으로 `project_duration` 일 동안 진행.

- **공휴일/주말 지연 (`holiday_delays`)**
  - 전체 공사 기간(start_date ~ start_date + project_duration − 1)을 달력으로 펼쳐,  
    토요일·일요일·법정 공휴일을 비근무일로 봅니다.
  - `holiday_delays = 비근무일(주말+공휴일) 개수 − 법정 공휴일 개수`  
    → 실질적으로 “주말 개수”에 해당.

- **날씨 지연 (`weather_delays`, 위험 기반 해석)**
  - `weather_forecast["days"]` 중 `construction_suitable == False` 인 날을 기상 불량일로 정의.
  - 기상 불량일은 **그날 실제 작업 여부와 무관하게**,  
    장비 안전 점검, 자재 이동 지연, 후속 공정 순서 변경 등으로  
    전체 일정 여유(buffer)를 줄이는 **위험일(risk day)** 로 간주합니다.
  - 따라서 **주말/공휴일(비근무일)에 발생한 기상 불량도 weather_delays 에 포함**됩니다.
  - 수식: `weather_delays = 기상 불량일 개수 = |bad_weather_dates|`.

- **최종 지연 및 공기**
  - `total_delay_days = holiday_delays + weather_delays`
  - `new_project_duration = project_duration + total_delay_days`

이 규칙은 `backend/scripts/run_llm_judge_example.py` 의 `build_business_rules()` 에 정의되어 있으며,  
그대로 Judge 시스템 프롬프트에 삽입됩니다.

#### 8.4 캘린더 팩트 고정 (weekend/holiday 사실값)

LLM이 달력을 다시 세다가 실수하지 않도록, **주말·비근무일 정보는 Python이 먼저 계산해서 제공**합니다.

- `build_calendar_facts(start_date_str, project_duration)`:
  - 전체 날짜 범위 (`calendar_range`: `[start, end]`)
  - 주말 날짜 리스트 (`weekend_dates`)
  - 주말 개수 (`weekend_count`)
- 이 값은 `scenario_inputs["calendar_facts"]` 로 Judge 에 전달되고,  
  프롬프트에서 **“이 값들은 이미 신뢰할 수 있는 facts 이므로, 달력을 다시 계산하지 말라”** 고 명시합니다.
- LLM은 이 facts 와 코드 출력(`holiday_impact["non_working_days"]`, `holiday_count`, `bad_weather_dates` 등)을 이용해  
  **순수하게 지연 계산 로직만** 검증하게 됩니다.

#### 8.5 Judge 출력 형식 (논문형 리포트 템플릿)

Judge에게는 **7개 섹션의 고정 템플릿**을 따라 답변하도록 요구합니다.

1. **전체 개념 요약**  
   - 이 시나리오에서 공기 지연을 어떻게 해석하는지,  
     특히 “비근무일의 기상 악화도 프로젝트 위험을 높이는가?”라는 관점에서 3~6문장으로 설명.
2. **수학적 계산 단계**  
   - `holiday_delays`, `weather_delays`, `total_delay_days`, `new_project_duration` 을  
     주어진 숫자(facts: non_working_days, holiday_count, bad_weather_dates 크기 등)에 따라  
     단계별로 계산 과정을 보여줌.
3. **코드 결과와 계산 결과 비교**  
   - 4개 지표에 대해 “코드 결과 / 규칙 기반 계산 결과 / 일치 여부”를 표로 제시.
4. **불일치 설명**  
   - 불일치가 있다면, 어느 수식·단계에서 차이가 나는지와 그 의미(예: 주말 처리, 날씨 해석 차이)를 서술.  
   - 모두 일치하면 “모든 항목이 규칙과 일치한다”고 명시.
5. **반복적으로 나타날 수 있는 시나리오**  
   - 예: 비근무일에만 악천후가 집중되는 경우, 연속된 악천후 기간 등,  
     이 로직이 특히 중요해지는 대표 시나리오를 1~2개 제시.
6. **전반적인 판정**  
   - 한 문장으로, 이 구현이 “규칙 및 현실적인 공정관리 관점에서 전반적으로 타당/부적합”한지 판정.
7. **정확도 점수**  
   - 형식: `**점수: X점**` (0~10점, 0점=완전히 잘못됨, 10점=규칙과 완전히 일치).  
   - 다음 줄에 `- 이유: ...` 형식으로 한 문장 이유를 쉬운 한국어로 설명.

이 구조 덕분에, **이 README (특히 본 섹션)를 그대로 GPT에 붙여넣으면**  
“모델 평가 및 검증 방법론”에 대한 **논문 형식의 서술**을 상당 부분 자동 생성할 수 있습니다.

#### 8.6 CSV/텍스트 로그 저장

- `run_llm_judge_example.py` 는 Judge 리포트를 콘솔에 출력함과 동시에,  
  `backend/scripts/llm_judge_results.txt` 에 핵심 정보를 행(row) 단위로 축적합니다.
- 저장되는 항목 예:
  - 시나리오 ID, 시작일, 공사 기간
  - 주말 개수 및 주말 날짜 (`weekend_count`, `weekend_dates`)
  - 코드가 계산한 `total_delay_days`, `holiday_delays`, `weather_delays`, `new_project_duration`
  - Judge 점수(`judge_score`) 및 한 줄 이유(`judge_reason`)
  - Judge 원문 리포트(`judge_report_raw`)
- 이 파일은 엑셀이나 Python(pandas)에서 쉽게 로드할 수 있어,  
  논문·보고서의 **실험 결과 표/그래프**를 구성하는 데이터로 바로 활용 가능합니다.

#### 8.7 RAG 기반 법규 검색(RAG Agent1) 정량 평가

법규 RAG 에이전트(LawRAGAgent, Agent1)는 별도의 **QA 벤치마크 세트**를 통해 정량 평가했습니다.

- **데이터 구축**
  - 건설 안전 규정 PDF로부터 도메인 전문가 검수를 거친 **질문–정답 쌍 약 520개**를 구축.
  - 각 질문에 대해 “올바른 법규 스니펫/조항”을 정답으로 태깅하고,  
    해당 텍스트를 FAISS 기반 임베딩 인덱스(`data/faiss/`)에 저장.
- **평가 방법**
  - 각 질문을 RAG 검색 쿼리로 사용하고, 상위 k개 스니펫을 반환하도록 LawRAGAgent 를 실행.
  - 반환된 순위 리스트를 정답 라벨과 비교하여, 다음 IR 지표를 계산:
    - **Precision@k**: 상위 k개 결과 중 정답에 해당하는 스니펫 비율.
    - **Recall@k**: 전체 정답 스니펫 중 상위 k개 안에 포함된 비율.
    - **MRR (Mean Reciprocal Rank)**: 첫 번째 정답 스니펫의 순위에 대한 역수의 평균.
    - **nDCG@k (normalized Discounted Cumulative Gain)**: 순위에 따른 가중치를 고려한 정규화된 이득.
    - **Hit@1 (Top‑1 Hit Rate)**: 가장 첫 번째 결과(Top‑1)가 정답 스니펫을 포함하는 비율.
- **활용**
  - 위 지표를 통해 인덱스 품질(임베딩/전처리)과 검색 전략(k 값, 스코어 커트라인 등)을 반복적으로 조정했습니다.
  - README 의 본 섹션과 평가 방법 설명을 그대로 GPT에 입력하면,  
    “RAG 기반 법규 검색 모듈의 정량 평가 방식”을 논문 형식으로 손쉽게 서술할 수 있습니다.

---

### 9. 사용 기술 스택 (Tech Stack)

#### 9.1 Backend

- **언어/프레임워크**
  - Python 3.10
  - FastAPI (비동기 웹 프레임워크)
  - Uvicorn (ASGI 서버)
  - Pydantic v2 (데이터 검증 및 모델 정의)

- **AI/데이터 처리**
  - `transformers`, `sentence-transformers` (사전학습 언어모델 및 임베딩)
  - `faiss-cpu` (법규 RAG 인덱스 검색)
  - `numpy`, `pandas`, `scikit-learn` (기본 수치·데이터 처리)

- **구성/유틸리티**
  - `python-dotenv` (환경변수 관리)
  - `requests` (외부 API 호출)
  - `pytest` (테스트)

#### 9.2 LLM / Prompting

- OpenAI API (예: `gpt-4o-mini`, `gpt-3.5-turbo`, `gpt-4` 등)
- 에이전트별 시스템/쿼리 프롬프트 파일 (`prompts/*.txt`)을 통해 역할과 출력을 **프롬프트 드리븐** 방식으로 제어

#### 9.3 Frontend (Flutter)

- Flutter (Material 3 기반 UI)
- Dart
- 주요 패키지:
  - `http` : 백엔드 REST API 호출
  - `google_fonts` : Noto Sans KR 폰트
- 특징:
  - `lib/home.dart` : 두 기능(일정 분석 / 법규 Q&A)을 선택하는 메인 허브
  - `lib/main.dart` : 일정 분석 + WBS 입력 + 결과 카드/테이블 스트리밍 렌더링
  - `lib/main2.dart` : 법규 Q&A 전용 화면, 법규 요약 카드 + 참고 문서 리스트 렌더링

#### 9.4 데이터 / 파일 포맷

- 법규 RAG 인덱스: FAISS (`index.faiss`) + 메타데이터 (`meta.jsonl`)
- 규칙 저장: JSON Lines (`data/rules/rules.jsonl`)
- LLM 프롬프트: UTF-8 텍스트 (`prompts/*.txt`)

---
