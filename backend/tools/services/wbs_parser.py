"""
WBS (Work Breakdown Structure) parser for natural language input.
"""
import re
from typing import List, Dict, Any, Optional
from ...schemas.io import WBSItem
from ...utils.prompt_loader import get_system_prompt, get_query_prompt


class WBSParser:
    """Parser for natural language WBS input."""
    
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
    
    def parse_wbs(self, wbs_text: str) -> List[WBSItem]:
        """
        Parse natural language WBS text into structured format.
        
        Args:
            wbs_text: Natural language WBS description
            
        Returns:
            List of WBSItem objects
        """
        # Use prompt-based parsing guidance
        try:
            parsing_prompt = get_query_prompt(
                "wbs_parser_query",
                wbs_text=wbs_text
            )
            # For now, we'll use the existing regex-based parsing
            # In a full LLM implementation, this would be used to guide the LLM
        except:
            # Fallback to existing method if prompt not available
            pass
        
        lines = [line.strip() for line in wbs_text.split('\n') if line.strip()]
        wbs_items = []
        
        for line in lines:
            try:
                item = self._parse_line(line)
                if item:
                    wbs_items.append(item)
            except Exception as e:
                print(f"Error parsing line '{line}': {e}")
                continue
        
        return wbs_items
    
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
