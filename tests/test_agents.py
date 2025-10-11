"""
Tests for agent functionality.
"""
import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock
from backend.agents.law_rag import LawRAGAgent
from backend.agents.threshold_builder import ThresholdBuilderAgent
from backend.agents.cpm_weather_cost import CPMWeatherCostAgent
from backend.agents.merger import MergerAgent
from backend.schemas.io import Citation, WBSItem, ChatResponse


class TestLawRAGAgent:
    """Test cases for LawRAGAgent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('backend.agents.law_rag.RagStoreFaiss'):
            self.agent = LawRAGAgent()
            self.agent.rag_store = None  # Simulate no FAISS store
    
    def test_search_regulations_fallback(self):
        """Test search regulations with fallback when FAISS not available."""
        citations = self.agent.search_regulations("타워크레인 풍속 기준")
        
        assert len(citations) > 0
        assert all(isinstance(c, Citation) for c in citations)
        assert all(c.document for c in citations)
        assert all(c.snippet for c in citations)
    
    def test_search_by_work_type(self):
        """Test search by work type."""
        citations = self.agent.search_by_work_type("CRANE")
        
        assert len(citations) > 0
        # Should include crane-related content
        crane_related = any("크레인" in c.snippet.lower() or "crane" in c.snippet.lower() 
                           for c in citations)
        assert crane_related
    
    def test_search_weather_conditions(self):
        """Test search for weather conditions."""
        citations = self.agent.search_weather_conditions("강풍")
        
        assert len(citations) > 0
        # Should include weather-related content
        weather_related = any("풍속" in c.snippet or "바람" in c.snippet 
                             for c in citations)
        assert weather_related
    
    def test_get_agent_status(self):
        """Test get agent status."""
        status = self.agent.get_agent_status()
        
        assert status["name"] == "Law RAG Agent"
        assert "search_capabilities" in status
        assert "fallback_mode" in status


class TestThresholdBuilderAgent:
    """Test cases for ThresholdBuilderAgent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('backend.agents.threshold_builder.RulesStore'):
            self.agent = ThresholdBuilderAgent()
            self.agent.rules_store = MagicMock()
    
    def test_build_rules_from_citations(self):
        """Test building rules from citations."""
        citations = [
            Citation(
                document="KOSHA 안전기준",
                page=1,
                snippet="타워크레인 작업 시 풍속 10m/s 이상에서 작업 중지",
                score=0.8
            ),
            Citation(
                document="건설안전규칙",
                page=2,
                snippet="콘크리트 타설 시 온도 5도 이하에서 작업 중지",
                score=0.7
            )
        ]
        
        rules = self.agent.build_rules(citations)
        
        assert len(rules) > 0
        assert all(rule.work_type for rule in rules)
        assert all(rule.metric for rule in rules)
        assert all(rule.confidence > 0 for rule in rules)
    
    def test_extract_work_type(self):
        """Test work type extraction."""
        work_type = self.agent._extract_work_type("타워크레인 작업 안전기준")
        assert work_type == "CRANE"
        
        work_type = self.agent._extract_work_type("콘크리트 타설 작업")
        assert work_type == "CONCRETE"
        
        work_type = self.agent._extract_work_type("일반적인 작업")
        assert work_type == "GENERAL"
    
    def test_get_unit_for_metric(self):
        """Test unit extraction for metrics."""
        assert self.agent._get_unit_for_metric("wind_speed") == "m/s"
        assert self.agent._get_unit_for_metric("temperature") == "°C"
        assert self.agent._get_unit_for_metric("rainfall") == "mm"
        assert self.agent._get_unit_for_metric("visibility") == "m"
        assert self.agent._get_unit_for_metric("unknown") == ""
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        citation = Citation(
            document="Test Doc",
            page=1,
            snippet="Test snippet",
            score=0.8
        )
        
        confidence = self.agent._calculate_confidence(citation, "풍속\\s*(\\d+(?:\\.\\d+)?)\\s*m/s")
        assert 0.5 <= confidence <= 1.0
    
    def test_deduplicate_rules(self):
        """Test rule deduplication."""
        from backend.schemas.io import RuleItem
        
        rules = [
            RuleItem(
                work_type="CRANE",
                metric="wind_speed",
                value=10.0,
                unit="m/s",
                source={},
                confidence=0.8,
                extracted_at=datetime.now(),
                note="Test"
            ),
            RuleItem(
                work_type="CRANE",
                metric="wind_speed",
                value=10.0,
                unit="m/s",
                source={},
                confidence=0.9,
                extracted_at=datetime.now(),
                note="Test"
            )
        ]
        
        unique_rules = self.agent._deduplicate_rules(rules)
        assert len(unique_rules) == 1
        assert unique_rules[0].confidence == 0.9  # Higher confidence kept
    
    def test_validate_rule(self):
        """Test rule validation."""
        from backend.schemas.io import RuleItem
        
        # Valid rule
        valid_rule = RuleItem(
            work_type="CRANE",
            metric="wind_speed",
            value=10.0,
            unit="m/s",
            source={},
            confidence=0.8,
            extracted_at=datetime.now(),
            note="Test"
        )
        
        validation = self.agent.validate_rule(valid_rule)
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        
        # Invalid rule
        invalid_rule = RuleItem(
            work_type="",
            metric="",
            value=None,
            unit="",
            source={},
            confidence=0.1,
            extracted_at=datetime.now(),
            note="Test"
        )
        
        validation = self.agent.validate_rule(invalid_rule)
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0


class TestCPMWeatherCostAgent:
    """Test cases for CPMWeatherCostAgent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('backend.agents.cpm_weather_cost.CPMService'), \
             patch('backend.agents.cpm_weather_cost.WeatherService'), \
             patch('backend.agents.cpm_weather_cost.HolidayService'), \
             patch('backend.agents.cpm_weather_cost.CostService'), \
             patch('backend.agents.cpm_weather_cost.RulesStore'):
            
            self.agent = CPMWeatherCostAgent()
    
    def test_analyze_empty_wbs(self):
        """Test analysis with empty WBS."""
        result = self.agent.analyze([], {}, [])
        
        assert "ideal_schedule" in result
        assert "delay_analysis" in result
        assert "cost_analysis" in result
        assert "recommendations" in result
        assert result["ideal_schedule"]["project_duration"] == 0
    
    def test_analyze_with_wbs(self):
        """Test analysis with WBS items."""
        wbs_items = [
            WBSItem(
                id="A",
                name="토공",
                duration=5,
                predecessors=[],
                work_type="EARTHWORK"
            ),
            WBSItem(
                id="B",
                name="콘크리트",
                duration=3,
                predecessors=[{"id": "A", "type": "FS", "lag": 0}],
                work_type="CONCRETE"
            )
        ]
        
        contract_data = {
            "contract_amount": 1000000000,
            "ld_rate": 0.0005,
            "indirect_cost_per_day": 1000000,
            "start_date": "2025-01-01"
        }
        
        # Mock the services
        self.agent.cpm_service.compute_cpm.return_value = {
            "tasks": [],
            "critical_path": ["A", "B"],
            "project_duration": 8
        }
        
        self.agent.weather_service.get_weather_forecast.return_value = {
            "days": []
        }
        
        self.agent.weather_service.get_construction_impact.return_value = {
            "unsuitable_days": 2
        }
        
        self.agent.holiday_service.get_holiday_impact.return_value = {
            "non_working_days": 1
        }
        
        self.agent.cost_service.compute_cost.return_value = {
            "indirect_cost": 2000000,
            "ld": 500000,
            "total": 2500000,
            "breakdown": []
        }
        
        result = self.agent.analyze(wbs_items, contract_data, [])
        
        assert result["ideal_schedule"]["project_duration"] == 8
        assert result["delay_analysis"]["total_delay_days"] == 3
        assert result["cost_analysis"]["total"] == 2500000
    
    def test_get_start_date(self):
        """Test start date extraction."""
        contract_data = {"start_date": "2025-01-01"}
        start_date = self.agent._get_start_date(contract_data)
        assert start_date == date(2025, 1, 1)
        
        contract_data = {"start_date": date(2025, 1, 1)}
        start_date = self.agent._get_start_date(contract_data)
        assert start_date == date(2025, 1, 1)
        
        contract_data = {}
        start_date = self.agent._get_start_date(contract_data)
        assert start_date == date.today()


class TestMergerAgent:
    """Test cases for MergerAgent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent = MergerAgent()
    
    def test_merge_results(self):
        """Test merging results from all agents."""
        results = {
            "law_rag": [
                Citation(
                    document="Test Doc",
                    page=1,
                    snippet="Test snippet",
                    score=0.8
                )
            ],
            "threshold_builder": [],
            "cpm_weather_cost": {
                "ideal_schedule": {
                    "tasks": [],
                    "critical_path": ["A", "B"],
                    "project_duration": 10
                },
                "delay_analysis": {
                    "total_delay_days": 2,
                    "delay_rows": []
                },
                "cost_analysis": {
                    "indirect_cost": 1000000,
                    "ld": 500000,
                    "total": 1500000
                }
            }
        }
        
        contract_data = {}
        
        response = self.agent.merge_results(results, contract_data)
        
        assert isinstance(response, ChatResponse)
        assert len(response.citations) == 1
        assert response.cost_summary.total == 1500000
        assert "tables" in response.ui
        assert "cards" in response.ui
    
    def test_build_citations(self):
        """Test building citations."""
        citations = [
            Citation(document="Doc1", page=1, snippet="Snippet1", score=0.9),
            Citation(document="Doc2", page=2, snippet="Snippet2", score=0.7),
            Citation(document="Doc3", page=3, snippet="Snippet3", score=0.8)
        ]
        
        result = self.agent._build_citations(citations)
        
        assert len(result) == 3
        assert result[0].score == 0.9  # Should be sorted by score
    
    def test_build_cost_summary(self):
        """Test building cost summary."""
        cost_analysis = {
            "indirect_cost": 1000000,
            "ld": 500000,
            "total": 1500000
        }
        
        result = self.agent._build_cost_summary(cost_analysis)
        
        assert result.indirect_cost == 1000000
        assert result.ld == 500000
        assert result.total == 1500000
    
    def test_get_agent_status(self):
        """Test get agent status."""
        status = self.agent.get_agent_status()
        
        assert status["name"] == "Merger Agent"
        assert "capabilities" in status
        assert "output_formats" in status
