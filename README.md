# Smart Construction Scheduling & Economic Analysis

AI-powered multi-agent system for construction project management with intelligent scheduling, weather impact analysis, and cost optimization.

## Features

- **🤖 LLM-Powered Multi-Agent System**: GPT-4/3.5 integrated into all agents for intelligent reasoning
- **🧠 Intelligent Intent Routing**: LLM-based supervisor understands natural language queries
- **📚 Smart RAG System**: FAISS vector search + LLM interpretation for construction regulations
- **📊 AI-Enhanced CPM Analysis**: LLM understands weather data and generates optimized schedules
- **💰 Intelligent Cost Analysis**: Automatic calculation with AI-driven recommendations
- **🌤️ Weather-Aware Scheduling**: Real-time weather integration with LLM-based impact analysis
- **📝 Natural Language Responses**: LLM generates clear, actionable insights in Korean
- **🎯 Prompt Management System**: Centralized prompt files for easy customization
- **🖥️ Modern Web UI**: React + Vite + Tailwind CSS frontend

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Data Layer    │
│   (React+Vite)  │◄──►│   (FastAPI)     │◄──►│   (FAISS+JSONL) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Multi-Agents  │
                    │                 │
                    │ • Law RAG       │
                    │ • Threshold     │
                    │ • CPM+Weather   │
                    │ • Merger        │
                    └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- FAISS index files (provided by another developer)

### Backend Setup

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd AI-CPM-project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
# .env 파일 생성 (자동으로 생성되지 않음)
cp .env.example .env  # Linux/Mac
copy .env.example .env  # Windows

# .env 파일 편집 (선택사항 - 기본값으로 개발 가능)
# - USE_STUB=true (stub 데이터 사용, 실제 API 불필요)
# - API 키는 나중에 필요할 때 추가
```

4. **데이터 디렉토리 확인:**
```bash
# 디렉토리 구조는 이미 준비되어 있습니다
# data/faiss/ - FAISS 인덱스 파일 위치 (.gitkeep 파일로 구조 유지)
# data/rules/ - 추출된 규칙 저장 위치 (.gitkeep 파일로 구조 유지)

# ⚠️ FAISS 인덱스가 없어도 서버는 정상 실행됩니다!
# FAISS 기능이 필요한 경우:
#   - index.faiss와 meta.jsonl을 data/faiss/에 배치
#   - 다른 개발자가 임베딩 파이프라인으로 생성
```

5. **Run the backend:**
```bash
uvicorn backend.app:app --reload
```

서버가 시작되면 FAISS 인덱스 경고가 표시될 수 있지만 정상입니다.

The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Run the frontend:**
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Usage

### Setup Contract

```bash
curl -X POST "http://localhost:8000/api/setup/contract" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_amount": 20000000000,
    "ld_rate": 0.0005,
    "indirect_cost_per_day": 3000000,
    "start_date": "2025-09-15",
    "calendar_policy": "5d"
  }'
```

### Analyze Project

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "비 예보 반영해서 다시 짜줘",
    "wbs_text": "A: 토공 5일, 선행 없음, 유형 EARTHWORK\nB: 콘크리트 3일, 선행 A(FS), 유형 CONCRETE"
  }'
```

### Refresh Rules

```bash
curl -X POST "http://localhost:8000/api/rules/refresh"
```

### Prompt Management

```bash
# Get available prompts
curl "http://localhost:8000/api/prompts"

# Get specific prompt
curl "http://localhost:8000/api/prompts/law_rag_system"

# Get agent status with prompts
curl "http://localhost:8000/api/agents/status"
```

## WBS Format

The system accepts natural language WBS descriptions:

```
A: 토공 굴착, 5일, 선행 없음, 유형 EARTHWORK
B: 기초 콘크리트, 3일, 선행 A(FS), 유형 CONCRETE
C: 타워크레인 설치, 2일, 선행 A(SS+1), 유형 CRANE
D: 철골 설치, 4일, 선행 B(FS), C(FS), 유형 STEEL
```

### Supported Predecessor Types:
- `FS`: Finish-to-Start (default)
- `SS`: Start-to-Start
- `FF`: Finish-to-Finish
- `SF`: Start-to-Finish

### Supported Work Types:
- `EARTHWORK`: 토공, 굴착
- `CONCRETE`: 콘크리트, 타설
- `CRANE`: 크레인, 타워크레인
- `STEEL`: 철골, 강재
- `ELECTRICAL`: 전기, 배선
- `PLUMBING`: 배관, 상하수도
- `FINISHING`: 마감, 마무리

## Configuration

### Environment Variables

```bash
# OpenAI Configuration (Required for LLM features)
OPENAI_API_KEY=your_openai_api_key_here

# LLM Model Settings
LLM_MODEL=gpt-4o-mini  # Options: gpt-4o-mini, gpt-4, gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Embeddings (Optional - for FAISS)
USE_OPENAI_EMBEDDINGS=false

# FAISS Configuration
FAISS_INDEX_PATH=./data/faiss/index.faiss
FAISS_META_PATH=./data/faiss/meta.jsonl
FAISS_TOP_K=5

# API Endpoints (placeholders)
KMA_ENDPOINT=<KMA_ENDPOINT>
KMA_API_KEY=
HOLIDAY_ENDPOINT=<HOLIDAY_ENDPOINT>
HOLIDAY_API_KEY=

# Development
USE_STUB=true
CURRENCY=KRW
```

**⚠️ Important**: You need an OpenAI API key for LLM features. Get one at https://platform.openai.com/api-keys

If no API key is provided:
- Supervisor falls back to regex-based routing
- Law RAG returns raw FAISS results without interpretation
- CPM Agent uses rule-based recommendations
- Merger skips natural language summary

## Testing

### 자동화된 테스트

Run the test suite:

```bash
# Backend tests
pytest tests/

# Specific test files
pytest tests/test_faiss_store.py
pytest tests/test_wbs_parser.py
pytest tests/test_agents.py
```

### API 테스트 도구들

서버가 실행 중일 때 다양한 방법으로 API를 테스트할 수 있습니다:

#### 1. **FastAPI 자동 문서 (가장 추천!)**

서버 실행 후 브라우저에서 접속:
```
http://localhost:8000/docs        # Swagger UI (대화형 API 문서)
http://localhost:8000/redoc       # ReDoc (API 레퍼런스)
```

#### 2. **웹 테스트 대시보드**

간단한 HTML 대시보드로 테스트:
```bash
# test_dashboard.html 파일을 브라우저에서 열기
# 또는 간단한 서버로 실행:
python -m http.server 3001
# 그 후 http://localhost:3001/test_dashboard.html 접속
```

기능:
- ✅ 서버 상태 실시간 확인
- ✅ 프롬프트 조회 및 확인
- ✅ 채팅 테스트 (WBS 포함)
- ✅ 에이전트 상태 모니터링
- ✅ 예제 질문 템플릿 제공

#### 3. **Python 테스트 스크립트**

자동화된 API 테스트:
```bash
# 서버가 실행 중인 상태에서
python test_api_client.py
```

모든 엔드포인트를 순차적으로 테스트하고 결과를 출력합니다.

#### 4. **HTTP 파일 (VSCode REST Client)**

VSCode의 REST Client 확장 사용:
```bash
# test_api_examples.http 파일을 VSCode에서 열고
# "Send Request" 클릭
```

#### 5. **Curl 명령어**

터미널에서 직접 테스트:
```bash
# 프롬프트 목록 확인
curl http://localhost:8000/api/prompts

# 특정 프롬프트 확인
curl http://localhost:8000/api/prompts/law_rag_system

# 에이전트 상태 확인
curl http://localhost:8000/api/agents/status

# 채팅 테스트
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "타워크레인 작업 시 풍속 기준은?"}'
```

### 프롬프트 디버깅

시스템이 어떤 프롬프트를 사용하는지 확인하려면:

```bash
# 1. 모든 프롬프트 목록
curl http://localhost:8000/api/prompts

# 2. 특정 에이전트의 시스템 프롬프트 확인
curl http://localhost:8000/api/agents/status

# 3. 프롬프트 파일 직접 확인
cat prompts/law_rag_system.txt
```

## Project Structure

```
project/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── config.py              # Configuration management
│   ├── supervisor.py          # Intent routing
│   ├── schemas/
│   │   └── io.py             # Request/response models
│   ├── agents/                # AI Agents (Chain execution)
│   │   ├── law_rag.py        # Law/Regulation RAG agent
│   │   ├── threshold_builder.py # Threshold extraction agent
│   │   ├── cpm_weather_cost.py  # CPM+Weather+Cost agent
│   │   └── merger.py         # Result merger agent
│   ├── tools/                 # Tools & Services (Used by agents)
│   │   ├── services/         # Utility services
│   │   │   ├── wbs_parser.py # WBS parser
│   │   │   ├── weather.py    # Weather service
│   │   │   ├── holidays.py   # Holiday service
│   │   │   ├── cpm.py        # CPM calculation
│   │   │   └── cost.py       # Cost calculation
│   │   ├── rag/              # RAG system
│   │   │   └── faiss_store.py # FAISS store
│   │   └── rules/            # Rules storage
│   │       └── store.py      # Rules management
│   └── utils/
│       └── prompt_loader.py  # Prompt management utility
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main React component
│   │   ├── main.tsx          # React entry point
│   │   └── components/
│   │       └── Tables.tsx    # Table components
│   ├── package.json
│   └── vite.config.ts
├── prompts/                  # Prompt files
│   ├── law_rag_system.txt    # Law RAG system prompt
│   ├── law_rag_query.txt     # Law RAG query prompt
│   ├── threshold_builder_system.txt # Threshold builder system prompt
│   ├── threshold_builder_extraction.txt # Threshold extraction prompt
│   ├── cpm_analysis_system.txt # CPM analysis system prompt
│   ├── cpm_analysis_query.txt # CPM analysis query prompt
│   ├── merger_system.txt     # Merger system prompt
│   ├── merger_formatting.txt # Merger formatting prompt
│   ├── wbs_parser_system.txt # WBS parser system prompt
│   ├── wbs_parser_query.txt  # WBS parser query prompt
│   └── supervisor_system.txt # Supervisor system prompt
├── data/
│   ├── faiss/                # FAISS index files
│   └── rules/                # Generated rules
├── tests/                    # Test files
├── requirements.txt
└── README.md
```

## Agents Overview

### 1. Supervisor (Intent Router)
- **LLM Mode**: GPT analyzes user intent in natural language → routes to appropriate agents
- **Fallback**: Regex pattern matching if LLM unavailable
- **Capability**: Understands complex queries and multi-intent requests

### 2. Law RAG Agent
- **LLM Mode**: FAISS search → GPT interprets and summarizes regulations for the query
- **Fallback**: Raw FAISS search results
- **Capability**: Contextual understanding and relevance filtering

### 3. Threshold Builder Agent
- **Current**: Regex-based numeric extraction (no LLM needed)
- **Capability**: Extracts safety thresholds from regulations
- **Output**: Structured rules (wind speed, temperature, etc.)

### 4. CPM Weather Cost Agent
- **LLM Mode**: Analyzes weather data → GPT generates intelligent schedule adjustments + actionable recommendations
- **Fallback**: Rule-based recommendations
- **Capability**: Understands weather impact context and suggests mitigation strategies

### 5. Merger Agent
- **LLM Mode**: GPT generates natural language summary of all analysis results
- **Fallback**: Structured data only
- **Capability**: Creates executive summary for project managers

## Prompt Management System

The system uses a centralized prompt management system for better maintainability and customization:

### Prompt Files Structure
- **System Prompts**: Define agent roles and capabilities
- **Query Prompts**: Format specific queries with variables
- **Extraction Prompts**: Guide data extraction and parsing

### Customizing Prompts
1. Edit prompt files in the `prompts/` directory
2. Use `{variable}` syntax for dynamic content
3. Restart the application to load changes
4. Use API endpoints to view current prompts

### Available Prompts
- `law_rag_system.txt` / `law_rag_query.txt`
- `threshold_builder_system.txt` / `threshold_builder_extraction.txt`
- `cpm_analysis_system.txt` / `cpm_analysis_query.txt`
- `merger_system.txt` / `merger_formatting.txt`
- `wbs_parser_system.txt` / `wbs_parser_query.txt`
- `supervisor_system.txt`

## Development Notes

- **🤖 LLM Integration**: OpenAI GPT-4/3.5 integrated across all agents
- **🔄 Graceful Fallbacks**: System works without LLM (reduced functionality)
- **⚙️ No Hard-coding**: All configuration through `.env` and `config.py`
- **🔌 Stub Mode**: Default mode uses stub data for external APIs
- **📖 Read-only FAISS**: No embedding generation, only search
- **🧩 Modular Design**: Each agent is independently testable
- **🛡️ Error Handling**: Graceful fallbacks when services unavailable
- **📝 Prompt-driven**: All agent behavior controlled by external prompt files
- **🏗️ Clean Architecture**: Clear separation between agents (business logic) and tools (utilities)

### LLM Integration Details

**When LLM is available (OpenAI API key set):**
1. **Supervisor**: Natural language understanding for intent routing
2. **Law RAG**: Contextual interpretation of regulations
3. **CPM Agent**: Intelligent weather impact analysis and recommendations
4. **Merger**: Executive summary generation in natural language

**When LLM is unavailable (no API key):**
1. **Supervisor**: Regex-based pattern matching
2. **Law RAG**: Raw FAISS search results
3. **CPM Agent**: Rule-based recommendations
4. **Merger**: Structured data only (no summary)

**All core functionality (CPM calculation, cost analysis, data processing) works independently of LLM.**

## Troubleshooting

### Clone 후 파일이 없어요!
**문제**: `.env` 파일이나 데이터 디렉토리가 없습니다
**해결**:
```bash
# 1. .env 파일 생성
cp .env.example .env  # Linux/Mac
copy .env.example .env  # Windows

# 2. 데이터 디렉토리는 이미 존재합니다
# data/faiss/.gitkeep와 data/rules/.gitkeep이 구조를 유지합니다

# 3. FAISS 인덱스가 없어도 서버는 실행됩니다 (USE_STUB=true)
```

### FAISS Index Not Found
```
Warning: FAISS index not found
```
**해결**: 
- 개발 중에는 무시해도 됩니다 (stub 모드 사용)
- FAISS 검색이 필요한 경우: `index.faiss`와 `meta.jsonl`을 `./data/faiss/`에 배치

### Pydantic RecursionError
**문제**: Pydantic v2에서 RecursionError 발생
**해결**: `schemas/io.py`에서 `Field()` 대신 기본값 직접 할당

### NumPy Compatibility Error
**문제**: FAISS와 NumPy 2.x 호환성 문제
**해결**: 
```bash
pip install "numpy<2.0"
```

### Frontend Connection Issues
**해결**: Backend가 8000번 포트에서 실행 중인지 확인

### Import Errors
**해결**: 가상환경 활성화 및 의존성 설치 확인
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

This project is licensed under the MIT License.