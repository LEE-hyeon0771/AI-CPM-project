# 🎛️ LLM 모델 설정 가이드

## 📋 목차
1. [빠른 시작](#빠른-시작)
2. [기본 설정](#기본-설정)
3. [에이전트별 설정](#에이전트별-설정)
4. [시나리오별 설정](#시나리오별-설정)
5. [실전 예제](#실전-예제)

---

## 🚀 빠른 시작

### 1. .env 파일 생성 (처음 한 번만)
```bash
# Windows
copy env.example.txt .env

# Linux/Mac
cp env.example.txt .env
```

### 2. OpenAI API 키 입력
`.env` 파일을 열어서:
```bash
OPENAI_API_KEY=sk-proj-your-actual-key-here  # ← 여기에 진짜 키 입력!
```

### 3. 서버 시작
```bash
uvicorn backend.app:app --reload
```

✅ 완료! 기본 설정(gpt-4o-mini)으로 작동합니다.

---

## ⚙️ 기본 설정

### Global LLM 설정 (모든 에이전트 기본값)

```bash
# .env 파일

# 모델 선택
LLM_MODEL=gpt-4o-mini
# 옵션: gpt-4o-mini, gpt-3.5-turbo, gpt-4, gpt-4-turbo, gpt-4o

# Temperature (응답 일관성 vs 창의성)
LLM_TEMPERATURE=0.7
# 0.0 = 매우 일관됨, 1.0 = 매우 창의적

# 최대 토큰 수 (응답 길이)
LLM_MAX_TOKENS=2000
# 1000 = 짧음, 3000 = 김
```

### 설정만 하면 모든 에이전트가 자동으로 사용!

---

## 🎯 에이전트별 설정

각 에이전트마다 **다른 모델**을 사용하고 싶다면:

### Supervisor (의도 분석)
```bash
SUPERVISOR_MODEL=gpt-4o-mini      # 빠른 모델 추천
SUPERVISOR_TEMPERATURE=0.3         # 일관된 라우팅
```
**역할**: 사용자 질문 분석 → 에이전트 선택
**추천**: 빠르고 저렴한 모델 (gpt-4o-mini)

---

### Law RAG Agent (법규 해석)
```bash
LAW_RAG_MODEL=gpt-4o-mini          # 또는 gpt-4 (정확도 중요 시)
LAW_RAG_TEMPERATURE=0.5            # 정확하면서도 이해하기 쉽게
```
**역할**: FAISS 검색 결과 → 사용자 질문에 맞게 해석
**추천**: 정확한 해석이 중요하면 gpt-4, 일반적으론 gpt-4o-mini

---

### CPM Weather Cost Agent (권장사항 생성)
```bash
CPM_MODEL=gpt-4o-mini              # 또는 gpt-4 (고품질 권장사항)
CPM_TEMPERATURE=0.8                # 다양한 대응 방안 생성
```
**역할**: 날씨 분석 → 일정 조정 권장사항 생성
**추천**: 창의적인 대응 방안이 필요하므로 높은 temperature

---

### Merger Agent (종합 요약)
```bash
MERGER_MODEL=gpt-4o-mini
MERGER_TEMPERATURE=0.6             # 명확하고 읽기 쉽게
```
**역할**: 모든 결과 통합 → 경영진용 요약
**추천**: 명확한 전달이 중요, gpt-4o-mini로 충분

---

## 💡 시나리오별 설정

### 시나리오 1: 개발/테스트 (기본, 추천! ⭐)

```bash
# 모두 gpt-4o-mini 사용
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
```

**비용**: 매우 저렴 (대화당 $0.001-0.003)
**품질**: 충분함
**속도**: 매우 빠름
**추천**: ✅ 대부분의 경우

---

### 시나리오 2: 저비용 프로덕션

```bash
# 모두 gpt-3.5-turbo 사용
LLM_MODEL=gpt-3.5-turbo
SUPERVISOR_MODEL=gpt-3.5-turbo
LAW_RAG_MODEL=gpt-3.5-turbo
CPM_MODEL=gpt-3.5-turbo
MERGER_MODEL=gpt-3.5-turbo
```

**비용**: 저렴 (gpt-4o-mini의 3배)
**품질**: 보통
**추천**: ⚠️ 예산 제한적일 때만

---

### 시나리오 3: 하이브리드 (전략적 배치 💎)

```bash
# 기본은 저렴하게
LLM_MODEL=gpt-4o-mini

# 중요한 곳만 고품질
SUPERVISOR_MODEL=gpt-4o-mini       # 라우팅은 간단
LAW_RAG_MODEL=gpt-4                # 법규는 정확하게!
CPM_MODEL=gpt-4                    # 권장사항도 정확하게!
MERGER_MODEL=gpt-4o-mini           # 요약은 간단히
```

**비용**: 중간 (전략적 배치)
**품질**: 중요한 곳만 최고
**추천**: ✅ 품질과 비용 균형

---

### 시나리오 4: 최고 품질 (비용 무관 🌟)

```bash
# 모두 최고 품질 모델
LLM_MODEL=gpt-4
SUPERVISOR_MODEL=gpt-4o            # 빠른 GPT-4
LAW_RAG_MODEL=gpt-4                # 최고 정확도
CPM_MODEL=gpt-4                    # 최고 품질 권장사항
MERGER_MODEL=gpt-4o                # 명확한 요약
```

**비용**: 매우 비쌈 (gpt-4o-mini의 200배)
**품질**: 최고
**추천**: ⚠️ 매우 중요한 프로젝트만

---

## 🔥 실전 예제

### 예제 1: 일반 개발자 (추천!)

```bash
# .env
OPENAI_API_KEY=sk-proj-abc123...
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# 에이전트별 설정은 생략 → 모두 Global 설정 사용
```

**결과**: 모든 에이전트가 gpt-4o-mini 사용
**비용**: 매우 저렴
**품질**: 충분함

---

### 예제 2: 법규 정확도 중요한 경우

```bash
# .env
OPENAI_API_KEY=sk-proj-abc123...
LLM_MODEL=gpt-4o-mini              # 기본은 저렴하게

# Law RAG만 고품질
LAW_RAG_MODEL=gpt-4                # 법규 해석은 정확하게!
LAW_RAG_TEMPERATURE=0.3            # 매우 일관되게
```

**결과**: 
- Supervisor: gpt-4o-mini (빠름)
- Law RAG: gpt-4 (정확함)
- CPM: gpt-4o-mini (충분)
- Merger: gpt-4o-mini (충분)

---

### 예제 3: 권장사항 품질 중요

```bash
# .env
OPENAI_API_KEY=sk-proj-abc123...
LLM_MODEL=gpt-4o-mini

# CPM만 고품질 + 창의적
CPM_MODEL=gpt-4
CPM_TEMPERATURE=0.9                # 매우 창의적!
```

**결과**: CPM 에이전트가 다양하고 창의적인 대응 방안 제시

---

### 예제 4: 프로덕션 (균형)

```bash
# .env
OPENAI_API_KEY=sk-proj-abc123...
LLM_MODEL=gpt-4o-mini

SUPERVISOR_MODEL=gpt-4o-mini
SUPERVISOR_TEMPERATURE=0.3         # 일관된 라우팅

LAW_RAG_MODEL=gpt-4o               # 빠르면서 정확
LAW_RAG_TEMPERATURE=0.5

CPM_MODEL=gpt-4o                   # 빠르면서 고품질
CPM_TEMPERATURE=0.7

MERGER_MODEL=gpt-4o-mini
MERGER_TEMPERATURE=0.6
```

**비용**: 중간
**품질**: 좋음
**속도**: 빠름

---

## 📊 Temperature 가이드

| Temperature | 특성 | 추천 용도 |
|-------------|------|-----------|
| 0.0 - 0.3 | 매우 일관됨, 예측 가능 | Supervisor (라우팅) |
| 0.4 - 0.6 | 균형잡힘 | Law RAG (법규 해석) |
| 0.7 - 0.8 | 약간 창의적 | CPM (권장사항), Merger |
| 0.9 - 1.0 | 매우 창의적, 다양함 | 브레인스토밍 |

---

## 🎯 모델별 특징

### gpt-4o-mini ⭐ (기본 추천)
- **비용**: 💰 매우 저렴
- **속도**: 🚀 매우 빠름
- **품질**: ✅ 좋음 (대부분 충분)
- **용도**: 일반 개발, 테스트, 대부분의 사용

### gpt-3.5-turbo
- **비용**: 💰 저렴 (gpt-4o-mini의 3배)
- **속도**: 🚀 빠름
- **품질**: ⚠️ 보통
- **용도**: 극도의 비용 절감 필요 시

### gpt-4o
- **비용**: 💸 비쌈 (gpt-4o-mini의 33배)
- **속도**: ⚡ 빠름
- **품질**: 🌟 매우 좋음
- **용도**: 프로덕션 (품질 중요)

### gpt-4
- **비용**: 💸 매우 비쌈 (gpt-4o-mini의 200배)
- **속도**: 🐢 느림
- **품질**: 🌟 최고
- **용도**: 매우 중요한 의사결정

---

## 🔄 설정 변경 방법

### 1. .env 파일 수정
```bash
# notepad .env (Windows)
# nano .env (Linux/Mac)

LLM_MODEL=gpt-4  # 변경!
```

### 2. 서버 재시작
```bash
# Ctrl+C로 중지 후
uvicorn backend.app:app --reload
```

### 3. 확인
```bash
# 로그에서 확인
INFO: Using model: gpt-4
```

---

## 💰 비용 계산기

### 평균 대화당 토큰 사용량
- Supervisor: ~500 토큰
- Law RAG: ~1500 토큰
- CPM: ~2000 토큰
- Merger: ~1000 토큰
- **총 1회 대화**: ~5000 토큰 (입력+출력)

### 대화당 예상 비용 (1000회 기준)

| 모델 | 1회 비용 | 1000회 비용 |
|------|---------|------------|
| gpt-4o-mini | $0.002 | **$2** ⭐ |
| gpt-3.5-turbo | $0.005 | $5 |
| gpt-4o | $0.05 | $50 |
| gpt-4 | $0.30 | $300 💸 |

**하이브리드 (Law + CPM만 GPT-4)**: ~$120 (1000회)

---

## ⚠️ 주의사항

### DO ✅
- ✅ 개발 중에는 `gpt-4o-mini` 사용
- ✅ 중요한 에이전트만 고품질 모델 사용
- ✅ Temperature를 에이전트 역할에 맞게 조정
- ✅ 비용 모니터링 (https://platform.openai.com/usage)

### DON'T ❌
- ❌ 모든 에이전트에 gpt-4 사용 (비용 폭발)
- ❌ Temperature 1.0 이상 사용 (일관성 떨어짐)
- ❌ .env 파일 Git 커밋 (보안 위험)
- ❌ API 키 공유

---

## 🎓 학습 팁

### 1단계: 기본 설정으로 시작
```bash
LLM_MODEL=gpt-4o-mini
```

### 2단계: 각 에이전트 응답 품질 확인

### 3단계: 필요한 에이전트만 고품질 모델로 업그레이드
```bash
LAW_RAG_MODEL=gpt-4  # 법규가 중요하면
```

### 4단계: Temperature 조정으로 미세 튜닝
```bash
LAW_RAG_TEMPERATURE=0.4  # 더 일관되게
```

---

## 📞 트러블슈팅

### "LLM이 설정되지 않았거나 오류가 발생했습니다"
**원인**: API 키 없음
**해결**: `.env`에서 `OPENAI_API_KEY` 확인

### "Rate limit exceeded"
**원인**: API 한도 초과
**해결**: 
1. 잠시 대기 (1분)
2. Tier 업그레이드
3. 더 저렴한 모델 사용

### "응답이 너무 느림"
**해결**:
```bash
LLM_MODEL=gpt-4o-mini  # 빠른 모델로 변경
LLM_MAX_TOKENS=1000    # 토큰 수 줄이기
```

---

## 🎯 추천 설정 요약

| 상황 | 추천 설정 |
|------|----------|
| **개발/테스트** | 모두 `gpt-4o-mini` ⭐ |
| **프로덕션 (일반)** | 모두 `gpt-4o-mini` |
| **프로덕션 (고품질)** | Law+CPM만 `gpt-4`, 나머지 `gpt-4o-mini` |
| **비용 최소화** | 모두 `gpt-3.5-turbo` |
| **최고 품질** | 모두 `gpt-4` 💸 |

---

## 📚 더 알아보기

- [OpenAI 모델 비교](https://platform.openai.com/docs/models)
- [OpenAI 가격](https://openai.com/pricing)
- [Temperature 이해하기](https://platform.openai.com/docs/guides/text-generation/parameter-details)

---

**이제 `.env` 파일을 수정하고 서버를 재시작하면 됩니다!** 🚀

