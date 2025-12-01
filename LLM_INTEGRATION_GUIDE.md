# 🤖 LLM 통합 가이드

## 개요

AI-CPM 프로젝트에 OpenAI GPT-4/3.5 모델이 통합되었습니다. 이 가이드는 LLM이 어디서 어떻게 사용되는지 설명합니다.

---

## 🎯 LLM이 사용되는 위치

### 1️⃣ Supervisor (의도 라우팅)
**파일**: `backend/supervisor.py`
**모델**: GPT-4o-mini (기본값)

#### 역할
- 사용자의 자연어 질문을 분석
- 필요한 에이전트를 지능적으로 선택
- 복잡한 다중 의도 쿼리 이해

#### 예시
```python
# 입력: "비 올 때 타워크레인 작업 중지 기준이랑 비용 알려줘"
# LLM 분석 결과:
{
  "intents": ["law_regulation", "weather", "cost"],
  "required_agents": ["law_rag", "threshold_builder", "cpm_weather_cost", "merger"],
  "reasoning": "법규 검색, 날씨 영향 분석, 비용 계산이 모두 필요"
}
```

#### Fallback
- OpenAI API 키 없으면 정규식 패턴 매칭 사용
- 기능 제한적이지만 기본 작동

---

### 2️⃣ Law RAG Agent (법규 검색 및 해석)
**파일**: `backend/agents/law_rag.py`
**모델**: GPT-4o-mini (기본값)

#### 역할
- FAISS 검색으로 관련 법규 찾기
- **LLM이 검색 결과를 사용자 질문에 맞게 해석하고 요약**
- 핵심 정보만 추출하여 제공

#### 예시
```python
# FAISS 검색 결과 (원본):
"타워크레인 작업 시 풍속 10m/s 이상에서 작업 중지. 
강우 시 즉시 작업 중지. 시정 100m 미만 시 작업 중지..."

# LLM 해석 후:
"타워크레인 작업 중지 기준: 풍속 10m/s 이상, 강우 발생 시

원문: 타워크레인 작업 시 풍속 10m/s..."
```

#### Fallback
- LLM 없으면 FAISS 검색 결과만 반환
- 해석 없이 원본 스니펫 제공

---

### 3️⃣ CPM Weather Cost Agent (일정 및 비용 분석)
**파일**: `backend/agents/cpm_weather_cost.py`
**모델**: GPT-4o-mini (기본값)

#### 역할
- 날씨 API 데이터를 **LLM이 이해하고 분석**
- 기상 조건에 따른 **지능적인 일정 조정 권장사항** 생성
- 구체적이고 실행 가능한 대응 방안 제시

#### 예시
```python
# 날씨 데이터:
# - 3일간 강풍 (12-15m/s)
# - 2일간 강우
# - 총 5일 작업 불가

# Rule-based (LLM 없음):
"프로젝트 지연 예상: 5일"
"기상 조건으로 인한 지연 예상 - 실내 작업 계획 수립"

# LLM-based (GPT 사용):
"핵심 리스크: 강풍과 강우로 인해 타워크레인 작업이 5일간 중단됩니다.

대응 방안:
1. 크레인 작업을 우선 일정으로 변경하여 날씨 좋은 날 집중 작업
2. 강우 기간에는 실내 배관·전기 작업으로 대체
3. 추가 크레인 투입을 검토하여 작업 기간 단축
4. 콘크리트 타설 일정을 날씨 예보 고려하여 조정

비용 절감 아이디어:
- 실내 작업 병행으로 간접비 최소화
- 사전 자재 준비로 날씨 회복 시 즉시 작업 재개"
```

#### Fallback
- 규칙 기반 권장사항만 제공
- 상황별 맞춤 조언 없음

---

### 4️⃣ Merger Agent (결과 통합 및 요약)
**파일**: `backend/agents/merger.py`
**모델**: GPT-4o-mini (기본값)

#### 역할
- 모든 에이전트 결과를 종합
- **LLM이 자연어로 경영진용 요약 생성**
- 핵심 의사결정 포인트 제시

#### 예시
```python
# LLM 생성 요약 (UI Card):
"💡 종합 분석

프로젝트는 기상 조건으로 5일 지연이 예상되며, 추가 비용은 2,500만원입니다. 
주요 원인은 강풍(3일)과 강우(2일)로 인한 타워크레인 작업 중단입니다. 
실내 작업 병행과 일정 조정으로 지연을 3일로 단축할 수 있습니다. 
즉시 대응 계획 수립을 권장합니다."
```

#### Fallback
- 구조화된 데이터만 제공
- 요약 카드 없음

---

## 🔧 설정 방법

### 1. OpenAI API 키 발급
1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭
3. 키 복사 (sk-proj-xxx...)

### 2. 환경 변수 설정
```bash
# env.example.txt를 .env로 복사
copy env.example.txt .env  # Windows
# 또는
cp env.example.txt .env    # Linux/Mac

# .env 파일 편집
OPENAI_API_KEY=sk-proj-your-actual-key-here
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

### 3. 서버 재시작
```bash
# 서버 중지 (Ctrl+C)
# 서버 재시작
uvicorn backend.app:app --reload
```

---

## 🧪 LLM 작동 확인

### 방법 1: Health Check
```bash
curl http://localhost:8000/api/agents/status
```

응답에서 각 에이전트의 `system_prompt` 확인

### 방법 2: 테스트 질문
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "비 오는 날 타워크레인 작업 중지 기준과 예상 비용 알려줘",
    "wbs_text": "타워크레인 설치, 10일\n콘크리트 타설, 5일"
  }'
```

**LLM이 작동하면**:
- `citations`에 요약된 법규 내용
- `ui.cards[0]`에 "💡 종합 분석" 카드
- 자세하고 맥락 있는 권장사항

**LLM이 없으면**:
- 원본 FAISS 검색 결과
- 종합 분석 카드 없음
- 간단한 규칙 기반 권장사항

---

## 💰 비용 관리

### GPT 모델별 비용 (2025년 기준)

| 모델 | Input (1M tokens) | Output (1M tokens) | 추천 용도 |
|------|-------------------|---------------------|-----------|
| **gpt-4o-mini** | $0.15 | $0.60 | ✅ 개발/테스트 (기본값) |
| **gpt-3.5-turbo** | $0.50 | $1.50 | 저렴한 프로덕션 |
| **gpt-4** | $30.00 | $60.00 | 고품질 필요 시 |

### 비용 절감 팁
1. **개발 중**: `LLM_MODEL=gpt-4o-mini` (기본값)
2. **디버깅**: API 키 제거하여 LLM 비활성화
3. **프로덕션**: 필요에 따라 gpt-3.5-turbo 또는 gpt-4 선택

---

## 📊 LLM 사용 흐름도

```
사용자 질문
    ↓
┌─────────────────────────────────────┐
│ 1. Supervisor (LLM)                 │
│ - 질문 분석                          │
│ - 에이전트 선택                      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. Law RAG Agent                    │
│ - FAISS 검색 (벡터)                 │
│ - LLM 해석 및 요약                  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. Threshold Builder                │
│ - Regex 추출 (LLM 불필요)           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 4. CPM Weather Cost Agent           │
│ - CPM 계산 (알고리즘)               │
│ - 날씨 영향 분석                    │
│ - LLM 권장사항 생성                 │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 5. Merger Agent (LLM)               │
│ - 결과 통합                         │
│ - 자연어 요약 생성                  │
│ - UI 컴포넌트 생성                  │
└─────────────────────────────────────┘
    ↓
최종 응답 (표, 그래프, 자연어 설명)
```

---

## 🔍 코드에서 LLM 확인하기

### LLM 클라이언트
```python
# backend/utils/llm_client.py
from backend.utils.llm_client import get_llm_client

llm = get_llm_client()

# LLM 호출
response = llm.chat_completion([
    {"role": "system", "content": "시스템 프롬프트"},
    {"role": "user", "content": "사용자 질문"}
])
```

### 각 에이전트에서
```python
# Supervisor
self.llm = get_llm_client()
if self.llm.is_available():
    return self._llm_route_intent(message)

# Law RAG
if self.llm.is_available() and citations:
    citations = self._enhance_citations_with_llm(query, citations)

# CPM Weather Cost
if self.llm.is_available():
    return self._llm_generate_recommendations(delay_analysis, cost_analysis)

# Merger
if self.llm.is_available():
    ui_response = self._enhance_with_llm_summary(...)
```

---

## 🚨 주의사항

### API 키 보안
- ⚠️ `.env` 파일을 **절대 Git에 커밋하지 마세요**
- ✅ `.gitignore`에 `.env` 포함되어 있는지 확인
- ✅ 환경 변수로만 관리

### 비용 모니터링
- OpenAI 사용량 대시보드: https://platform.openai.com/usage
- 예상 비용 계산:
  - 한 번의 대화: 약 1,000-3,000 토큰
  - gpt-4o-mini: 대화당 $0.001-0.003
  - gpt-4: 대화당 $0.03-0.09

### Rate Limits
- 무료 계정: 분당 3 요청, 시간당 200 요청
- Tier 1: 분당 500 요청
- 초과 시 에러 → 자동으로 fallback 모드 작동

---

## 🧪 테스트 시나리오

### 시나리오 1: LLM 없이 테스트
```bash
# .env 파일에서 API 키 제거 또는 주석 처리
# OPENAI_API_KEY=

# 서버 시작
uvicorn backend.app:app --reload

# 테스트 - 기본 기능만 작동 (fallback 모드)
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "타워크레인 풍속 기준"}'
```

**결과**: 
- ✅ 작동함 (fallback citations)
- ⚠️ 해석 없는 원본 데이터만
- ⚠️ 종합 분석 없음

### 시나리오 2: LLM과 함께 테스트
```bash
# .env 파일에 API 키 설정
OPENAI_API_KEY=sk-proj-your-key

# 서버 재시작
uvicorn backend.app:app --reload

# 동일한 테스트
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "타워크레인 풍속 기준과 예상 지연일"}'
```

**결과**:
- ✅ 해석된 법규 내용
- ✅ 맥락 있는 권장사항
- ✅ "💡 종합 분석" 카드 추가
- ✅ 자연어 요약

---

## 🎛️ 모델 선택 가이드

### gpt-4o-mini (기본값, 추천)
- ✅ **가격**: 매우 저렴
- ✅ **속도**: 빠름
- ✅ **품질**: 이 프로젝트에 충분
- 👍 **추천**: 개발 및 대부분의 사용 사례

### gpt-3.5-turbo
- ✅ **가격**: 저렴
- ⚠️ **품질**: gpt-4o-mini보다 낮음
- 🤔 **사용**: 레거시 호환성 필요 시

### gpt-4
- ⚠️ **가격**: 매우 비쌈 (200배)
- ✅ **품질**: 최고
- 🎯 **사용**: 복잡한 분석, 중요한 의사결정

### 변경 방법
```bash
# .env 파일에서
LLM_MODEL=gpt-4o-mini  # 또는 gpt-4, gpt-3.5-turbo
```

---

## 🐛 트러블슈팅

### "LLM이 설정되지 않았거나 오류가 발생했습니다"
**원인**: OpenAI API 키가 없거나 잘못됨
**해결**:
```bash
# .env 파일 확인
OPENAI_API_KEY=sk-proj-... # 올바른 형식

# 키 테스트
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### "Rate limit exceeded"
**원인**: API 요청 한도 초과
**해결**:
1. 잠시 대기 (1분)
2. Tier 업그레이드 (결제)
3. 또는 fallback 모드로 사용 (API 키 제거)

### LLM 응답이 느림
**원인**: GPT-4 사용 중이거나 네트워크 지연
**해결**:
```bash
# 더 빠른 모델로 변경
LLM_MODEL=gpt-4o-mini

# 토큰 제한 줄이기
LLM_MAX_TOKENS=1000
```

---

## 📈 성능 최적화

### Temperature 조정
```bash
# 더 일관된 응답 (추천)
LLM_TEMPERATURE=0.3

# 더 창의적인 응답
LLM_TEMPERATURE=0.9
```

### Max Tokens 조정
```bash
# 짧은 응답 (빠름, 저렴)
LLM_MAX_TOKENS=500

# 긴 상세 응답
LLM_MAX_TOKENS=3000
```

---

## ✅ 체크리스트

LLM 통합 완료 확인:
- [x] `backend/utils/llm_client.py` 생성
- [x] `backend/config.py`에 LLM 설정 추가
- [x] Supervisor에 LLM 통합
- [x] Law RAG Agent에 LLM 통합
- [x] CPM Weather Cost Agent에 LLM 통합
- [x] Merger Agent에 LLM 통합
- [x] 모든 에이전트에 fallback 메커니즘
- [x] 환경 변수 예제 파일 (`env.example.txt`)
- [x] README 업데이트
- [x] 테스트 도구 제공

---

## 🎯 다음 단계

1. **OpenAI API 키 설정**
2. **서버 재시작**
3. **http://localhost:8000/docs에서 테스트**
4. **실제 질문으로 LLM 기능 확인**

LLM이 작동하면 훨씬 더 지능적이고 맥락 있는 응답을 받을 수 있습니다! 🚀

