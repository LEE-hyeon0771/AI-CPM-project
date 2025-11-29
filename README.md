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

### 8. 사용 기술 스택 (Tech Stack)

#### 8.1 Backend

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

#### 8.2 LLM / Prompting

- OpenAI API (예: `gpt-4o-mini`, `gpt-3.5-turbo`, `gpt-4` 등)
- 에이전트별 시스템/쿼리 프롬프트 파일 (`prompts/*.txt`)을 통해 역할과 출력을 **프롬프트 드리븐** 방식으로 제어

#### 8.3 Frontend (Flutter)

- Flutter (Material 3 기반 UI)
- Dart
- 주요 패키지:
  - `http` : 백엔드 REST API 호출
  - `google_fonts` : Noto Sans KR 폰트
- 특징:
  - `lib/home.dart` : 두 기능(일정 분석 / 법규 Q&A)을 선택하는 메인 허브
  - `lib/main.dart` : 일정 분석 + WBS 입력 + 결과 카드/테이블 스트리밍 렌더링
  - `lib/main2.dart` : 법규 Q&A 전용 화면, 법규 요약 카드 + 참고 문서 리스트 렌더링

#### 8.4 데이터 / 파일 포맷

- 법규 RAG 인덱스: FAISS (`index.faiss`) + 메타데이터 (`meta.jsonl`)
- 규칙 저장: JSON Lines (`data/rules/rules.jsonl`)
- LLM 프롬프트: UTF-8 텍스트 (`prompts/*.txt`)

---
