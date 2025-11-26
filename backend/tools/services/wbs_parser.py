"""
WBS (Work Breakdown Structure) parser for natural language input.

기본적으로는 기존의 규칙 기반(정규식) 파서를 사용하되,
자연어로만 작성된 입력에 대해서는 LLM을 사용하여 WBS 구조를 추출합니다.
"""
import re
import json
from typing import List, Dict, Any, Optional
from ...schemas.io import WBSItem
from ...utils.prompt_loader import get_query_prompt
from ...utils.llm_client import get_llm_client
from ...config import get_settings


class WBSParser:
    """Parser for natural language WBS input (LLM + 규칙 기반 혼합)."""
    
    def __init__(self):
        # Predecessor relationship patterns
        self.predecessor_patterns = {
            "FS": r"FS|완료시작|finish-start",
            "SS": r"SS|시작시작|start-start", 
            "FF": r"FF|완료완료|finish-finish",
            "SF": r"SF|시작완료|start-finish"
        }
        
        # Work type mappings
        self.work_type_mappings = {
            "EARTHWORK": ["토공", "굴착", "땅파기", "지반", "earthwork"],
            "CONCRETE": ["콘크리트", "타설", "거푸집", "concrete"],
            "CRANE": ["크레인", "타워크레인", "호이스트", "crane"],
            "STEEL": ["철골", "강재", "구조", "steel"],
            "ELECTRICAL": ["전기", "배선", "전력", "electrical"],
            "PLUMBING": ["배관", "상하수도", "급수", "plumbing"],
            "FINISHING": ["마감", "마무리", "finishing"]
        }

        self.settings = get_settings()
        self.llm = get_llm_client()
    
    def parse_wbs(self, wbs_text: str) -> List[WBSItem]:
        """
        Parse natural language WBS text into structured format.
        
        1) 규칙 기반 파서로 시도
        2) 충분히 파싱되지 않으면, LLM을 사용해 구조화된 WBS(JSON)를 생성
        
        Args:
            wbs_text: Natural language WBS description
            
        Returns:
            List of WBSItem objects
        """
        wbs_text = wbs_text or ""

        # 1) 우선 기존 라인 기반 파싱 시도 (기존 테스트/포맷 호환)
        lines = [line.strip() for line in wbs_text.split("\n") if line.strip()]
        wbs_items: List[WBSItem] = []
        
        for line in lines:
            try:
                item = self._parse_line(line)
                if item:
                    wbs_items.append(item)
            except Exception as e:
                print(f"Error parsing line '{line}': {e}")
                continue

        # 규칙 기반으로 어느 정도 성공했다면 그대로 반환
        if len(wbs_items) >= 1:
            return wbs_items

        # 2) 구조화된 라인이 거의 없다면, LLM 기반 파싱 시도
        if not self.llm.is_available():
            # LLM 사용 불가 시, 규칙 기반 결과(없으면 빈 리스트) 반환
            # 마지막으로 휴리스틱 자연어 파싱 시도
            return self._heuristic_parse_freeform(wbs_text)

        try:
            llm_items = self._llm_parse_wbs(wbs_text)
            if llm_items:
                return llm_items
            # LLM이 빈 결과를 주면 휴리스틱 파서로 재시도
            return self._heuristic_parse_freeform(wbs_text)
        except Exception as e:
            print(f"LLM WBS parsing error: {e}")
            # 실패 시에도 최소한 휴리스틱 자연어 파싱을 한 번 더 시도
            heuristic_items = self._heuristic_parse_freeform(wbs_text)
            return heuristic_items
    
    def _llm_parse_wbs(self, wbs_text: str) -> List[WBSItem]:
        """Use LLM to parse completely natural WBS text into WBSItem list."""
        prompt = get_query_prompt(
            "wbs_parser_query",
            wbs_text=wbs_text
        )

        response_text = self.llm.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "당신은 건설 프로젝트의 WBS를 구조화하는 전문가입니다. 반드시 JSON 배열만 출력합니다."
                },
                {"role": "user", "content": prompt}
            ],
            model=self.settings.cpm_model,
            temperature=self.settings.cpm_temperature,
        )

        # 응답에서 JSON 배열 부분만 최대한 안전하게 추출
        text = response_text.strip()

        # 1) ```json ... ``` 코드블록 제거
        if "```" in text:
            try:
                fenced = text.split("```")
                # fenced 사이에서 JSON 배열이 포함된 부분을 탐색
                candidates = [part for part in fenced if "[" in part and "]" in part]
                if candidates:
                    text = candidates[0]
            except Exception:
                pass

        # 2) 처음 나타나는 '['부터 마지막 ']'까지를 JSON으로 가정
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end >= start:
            text = text[start : end + 1]

        data = json.loads(text)

        items: List[WBSItem] = []
        if isinstance(data, list):
            for obj in data:
                try:
                    # 기본 키 매핑을 가정: id, name, duration, work_type, predecessors
                    items.append(WBSItem(**obj))
                except Exception as e:
                    print(f"Error converting LLM WBS item {obj}: {e}")
                    continue

        return items

    def _heuristic_parse_freeform(self, wbs_text: str) -> List[WBSItem]:
        """
        LLM이나 규칙 기반 라인 파싱이 모두 실패했을 때,
        완전 자연어 문장에서 간단한 패턴으로 WBS를 추출하는 휴리스틱 파서.

        예시 문장:
        "기초 토공 굴착을 5일 동안 하고, 바로 이어서 기초 콘크리트를 3일,
         그 다음 구조 골조 타설을 10일, 마지막으로 마감 공사를 7일 진행한다."
        """
        text = (wbs_text or "").strip()
        if not text:
            return []

        # 문장을 여러 개의 작업 덩어리로 분리
        # 한국어 접속어 + 마침표 + 줄바꿈 등을 기준으로 나눔
        chunks = re.split(r"[\.。\n]|그리고|그 다음|그다음|마지막으로|바로 이어서", text)
        chunks = [c.strip() for c in chunks if c.strip()]

        items: List[WBSItem] = []
        current_id_ord = ord("A")
        prev_id: Optional[str] = None

        for chunk in chunks:
            # "작업명을 N일" 패턴 찾기
            # 예: "기초 토공 굴착을 5일 동안", "기초 콘크리트를 3일"
            m = re.search(r"(.+?)를\s*(\d+)\s*일", chunk)
            if not m:
                m = re.search(r"(.+?)\s*(\d+)\s*일", chunk)
            if not m:
                continue

            name = m.group(1).strip()
            try:
                duration = int(m.group(2))
            except ValueError:
                duration = 1

            task_id = chr(current_id_ord)
            current_id_ord += 1

            # 선행 관계: 단순히 바로 앞 작업을 FS로 연결
            predecessors: List[Dict[str, Any]] = []
            if prev_id is not None:
                predecessors.append({"id": prev_id, "type": "FS", "lag": 0})

            work_type = self._infer_work_type(name)

            try:
                items.append(
                    WBSItem(
                        id=task_id,
                        name=name,
                        duration=duration,
                        predecessors=predecessors,
                        work_type=work_type,
                    )
                )
                prev_id = task_id
            except Exception as e:
                print(f"Error creating heuristic WBS item from chunk '{chunk}': {e}")
                continue

        return items
    
    def _parse_line(self, line: str) -> Optional[WBSItem]:
        """Parse a single WBS line."""
        # Pattern: ID: Name, Duration, Predecessors, WorkType
        # Example: "A: 토공 굴착, 5일, 선행 없음, 유형 EARTHWORK"
        
        # Extract ID and rest of the line
        id_match = re.match(r'^([A-Z0-9]+):\s*(.*)', line)
        if not id_match:
            return None
        
        task_id = id_match.group(1)
        rest = id_match.group(2)
        
        # Split by commas
        parts = [part.strip() for part in rest.split(',')]
        
        if len(parts) < 2:
            return None
        
        # Extract name and duration
        name = parts[0]
        duration = self._extract_duration(parts[1])
        
        # Extract predecessors
        predecessors = []
        if len(parts) > 2 and "선행" in parts[2] and "없음" not in parts[2]:
            predecessors = self._parse_predecessors(parts[2])
        
        # Extract work type
        work_type = "GENERAL"
        if len(parts) > 3:
            work_type = self._extract_work_type(parts[3])
        else:
            # Try to infer from name
            work_type = self._infer_work_type(name)
        
        return WBSItem(
            id=task_id,
            name=name,
            duration=duration,
            predecessors=predecessors,
            work_type=work_type
        )
    
    def _extract_duration(self, duration_text: str) -> int:
        """Extract duration in days from text."""
        # Look for numbers followed by "일" or "day"
        match = re.search(r'(\d+)\s*(?:일|day)', duration_text)
        if match:
            return int(match.group(1))
        
        # Fallback: look for any number
        match = re.search(r'(\d+)', duration_text)
        if match:
            return int(match.group(1))
        
        return 1  # Default duration
    
    def _parse_predecessors(self, predecessor_text: str) -> List[Dict[str, Any]]:
        """Parse predecessor relationships."""
        predecessors = []
        
        # Remove "선행" prefix
        text = re.sub(r'선행\s*', '', predecessor_text)
        
        # Split by common separators
        parts = re.split(r'[,;]', text)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Parse individual predecessor
            pred = self._parse_single_predecessor(part)
            if pred:
                predecessors.append(pred)
        
        return predecessors
    
    def _parse_single_predecessor(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse a single predecessor relationship."""
        # Pattern: ID(RELATIONSHIP+LAG) or just ID
        # Examples: "A(FS)", "B(SS+1)", "C"
        
        # Check for relationship type
        relationship = "FS"  # Default
        lag = 0
        
        # Look for relationship pattern
        for rel_type, pattern in self.predecessor_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                relationship = rel_type
                break
        
        # Extract ID and lag
        match = re.search(r'([A-Z0-9]+)(?:\([^)]*([+-]?\d*)\))?', text)
        if match:
            pred_id = match.group(1)
            lag_text = match.group(2) if match.group(2) else "0"
            
            try:
                lag = int(lag_text) if lag_text else 0
            except ValueError:
                lag = 0
            
            return {
                "id": pred_id,
                "type": relationship,
                "lag": lag
            }
        
        return None
    
    def _extract_work_type(self, work_type_text: str) -> str:
        """Extract work type from text."""
        # Remove common prefixes
        text = re.sub(r'유형\s*', '', work_type_text, flags=re.IGNORECASE)
        text = text.strip().upper()
        
        # Direct match
        if text in self.work_type_mappings:
            return text
        
        # Check mappings
        for work_type, keywords in self.work_type_mappings.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    return work_type
        
        return "GENERAL"
    
    def _infer_work_type(self, name: str) -> str:
        """Infer work type from task name."""
        name_lower = name.lower()
        
        for work_type, keywords in self.work_type_mappings.items():
            for keyword in keywords:
                if keyword.lower() in name_lower:
                    return work_type
        
        return "GENERAL"
    
    def validate_wbs(self, wbs_items: List[WBSItem]) -> List[str]:
        """Validate WBS for common issues."""
        errors = []
        task_ids = set()
        
        for item in wbs_items:
            # Check for duplicate IDs
            if item.id in task_ids:
                errors.append(f"Duplicate task ID: {item.id}")
            task_ids.add(item.id)
            
            # Check duration
            if item.duration <= 0:
                errors.append(f"Invalid duration for task {item.id}: {item.duration}")
            
            # Check predecessors
            for pred in item.predecessors:
                if pred["id"] not in task_ids and pred["id"] != item.id:
                    # This might be a forward reference, which is OK
                    pass
        
        return errors
