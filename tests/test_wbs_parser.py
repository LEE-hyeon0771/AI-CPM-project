"""
Tests for WBS parser functionality.
"""
import pytest
from backend.tools.services.wbs_parser import WBSParser
from backend.schemas.io import WBSItem


class TestWBSParser:
    """Test cases for WBSParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = WBSParser()
    
    def test_parse_simple_wbs(self):
        """Test parsing simple WBS text."""
        wbs_text = """
        A: 토공 굴착, 5일, 선행 없음, 유형 EARTHWORK
        B: 기초 콘크리트, 3일, 선행 A(FS), 유형 CONCRETE
        """
        
        result = self.parser.parse_wbs(wbs_text)
        
        assert len(result) == 2
        
        # Check first task
        assert result[0].id == "A"
        assert result[0].name == "토공 굴착"
        assert result[0].duration == 5
        assert result[0].work_type == "EARTHWORK"
        assert len(result[0].predecessors) == 0
        
        # Check second task
        assert result[1].id == "B"
        assert result[1].name == "기초 콘크리트"
        assert result[1].duration == 3
        assert result[1].work_type == "CONCRETE"
        assert len(result[1].predecessors) == 1
        assert result[1].predecessors[0]["id"] == "A"
        assert result[1].predecessors[0]["type"] == "FS"
    
    def test_parse_complex_predecessors(self):
        """Test parsing complex predecessor relationships."""
        wbs_text = """
        A: 토공, 5일, 선행 없음, 유형 EARTHWORK
        B: 콘크리트, 3일, 선행 A(SS+1), 유형 CONCRETE
        C: 마감, 2일, 선행 B(FF), 유형 FINISHING
        """
        
        result = self.parser.parse_wbs(wbs_text)
        
        assert len(result) == 3
        
        # Check SS+1 relationship
        assert result[1].predecessors[0]["type"] == "SS"
        assert result[1].predecessors[0]["lag"] == 1
        
        # Check FF relationship
        assert result[2].predecessors[0]["type"] == "FF"
        assert result[2].predecessors[0]["lag"] == 0
    
    def test_parse_multiple_predecessors(self):
        """Test parsing multiple predecessors."""
        wbs_text = """
        A: 토공, 5일, 선행 없음, 유형 EARTHWORK
        B: 콘크리트, 3일, 선행 없음, 유형 CONCRETE
        C: 마감, 2일, 선행 A(FS), B(FS), 유형 FINISHING
        """
        
        result = self.parser.parse_wbs(wbs_text)
        
        assert len(result) == 3
        assert len(result[2].predecessors) == 2
        
        pred_ids = [p["id"] for p in result[2].predecessors]
        assert "A" in pred_ids
        assert "B" in pred_ids
    
    def test_parse_work_type_inference(self):
        """Test work type inference from task names."""
        wbs_text = """
        A: 토공 굴착 작업, 5일, 선행 없음
        B: 콘크리트 타설, 3일, 선행 A(FS)
        C: 타워크레인 설치, 2일, 선행 A(SS)
        """
        
        result = self.parser.parse_wbs(wbs_text)
        
        assert result[0].work_type == "EARTHWORK"
        assert result[1].work_type == "CONCRETE"
        assert result[2].work_type == "CRANE"
    
    def test_parse_duration_extraction(self):
        """Test duration extraction from various formats."""
        wbs_text = """
        A: 작업1, 5일, 선행 없음
        B: 작업2, 3 day, 선행 A(FS)
        C: 작업3, 7, 선행 B(FS)
        """
        
        result = self.parser.parse_wbs(wbs_text)
        
        assert result[0].duration == 5
        assert result[1].duration == 3
        assert result[2].duration == 7
    
    def test_parse_empty_input(self):
        """Test parsing empty input."""
        result = self.parser.parse_wbs("")
        assert len(result) == 0
        
        result = self.parser.parse_wbs("   \n  \n  ")
        assert len(result) == 0
    
    def test_parse_invalid_lines(self):
        """Test parsing lines with invalid format."""
        wbs_text = """
        A: 토공 굴착, 5일, 선행 없음, 유형 EARTHWORK
        Invalid line without proper format
        B: 기초 콘크리트, 3일, 선행 A(FS), 유형 CONCRETE
        """
        
        result = self.parser.parse_wbs(wbs_text)
        
        # Should only parse valid lines
        assert len(result) == 2
        assert result[0].id == "A"
        assert result[1].id == "B"
    
    def test_validate_wbs(self):
        """Test WBS validation."""
        # Valid WBS
        valid_wbs = [
            WBSItem(id="A", name="Task A", duration=5, predecessors=[], work_type="EARTHWORK"),
            WBSItem(id="B", name="Task B", duration=3, predecessors=[{"id": "A", "type": "FS", "lag": 0}], work_type="CONCRETE")
        ]
        
        errors = self.parser.validate_wbs(valid_wbs)
        assert len(errors) == 0
        
        # Invalid WBS with duplicate IDs
        invalid_wbs = [
            WBSItem(id="A", name="Task A", duration=5, predecessors=[], work_type="EARTHWORK"),
            WBSItem(id="A", name="Task B", duration=3, predecessors=[], work_type="CONCRETE")
        ]
        
        errors = self.parser.validate_wbs(invalid_wbs)
        assert len(errors) == 1
        assert "Duplicate task ID: A" in errors[0]
        
        # Invalid WBS with negative duration
        invalid_wbs2 = [
            WBSItem(id="A", name="Task A", duration=-1, predecessors=[], work_type="EARTHWORK")
        ]
        
        errors = self.parser.validate_wbs(invalid_wbs2)
        assert len(errors) == 1
        assert "Invalid duration" in errors[0]
    
    def test_extract_duration_edge_cases(self):
        """Test duration extraction edge cases."""
        # Test with no number
        duration = self.parser._extract_duration("no number here")
        assert duration == 1  # Default duration
        
        # Test with multiple numbers (should take first)
        duration = self.parser._extract_duration("5일 후 3일 더")
        assert duration == 5
    
    def test_parse_single_predecessor_edge_cases(self):
        """Test single predecessor parsing edge cases."""
        # Test with invalid format
        result = self.parser._parse_single_predecessor("invalid format")
        assert result is None
        
        # Test with just ID
        result = self.parser._parse_single_predecessor("A")
        assert result is not None
        assert result["id"] == "A"
        assert result["type"] == "FS"  # Default
        assert result["lag"] == 0
    
    def test_extract_work_type_edge_cases(self):
        """Test work type extraction edge cases."""
        # Test with empty text
        work_type = self.parser._extract_work_type("")
        assert work_type == "GENERAL"
        
        # Test with unknown work type
        work_type = self.parser._extract_work_type("UNKNOWN_WORK_TYPE")
        assert work_type == "GENERAL"
