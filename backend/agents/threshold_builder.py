"""
Threshold Builder Agent for extracting numeric rules from RAG snippets.
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..schemas.io import Citation, RuleItem
from ..tools.rules.store import RulesStore
from ..utils.prompt_loader import get_system_prompt, get_query_prompt


class ThresholdBuilderAgent:
    """Agent for building numeric rules from RAG snippets."""
    
    def __init__(self):
        self.rules_store = RulesStore()
        
        # Regex patterns for extracting numeric values
        self.patterns = {
            "wind_speed": [
                r"풍속\s*(\d+(?:\.\d+)?)\s*m/s",
                r"바람\s*(\d+(?:\.\d+)?)\s*m/s",
                r"(\d+(?:\.\d+)?)\s*m/s.*풍속",
                r"풍속.*(\d+(?:\.\d+)?)\s*m/s"
            ],
            "temperature": [
                r"온도\s*(\d+(?:\.\d+)?)\s*도",
                r"기온\s*(\d+(?:\.\d+)?)\s*도",
                r"(\d+(?:\.\d+)?)\s*도.*이하",
                r"(\d+(?:\.\d+)?)\s*도.*이상"
            ],
            "rainfall": [
                r"강우\s*(\d+(?:\.\d+)?)\s*mm",
                r"강수량\s*(\d+(?:\.\d+)?)\s*mm",
                r"(\d+(?:\.\d+)?)\s*mm.*강우"
            ],
            "visibility": [
                r"시정\s*(\d+(?:\.\d+)?)\s*m",
                r"가시거리\s*(\d+(?:\.\d+)?)\s*m",
                r"(\d+(?:\.\d+)?)\s*m.*시정"
            ]
        }
        
        # Work type mappings
        self.work_type_mappings = {
            "CRANE": ["크레인", "타워크레인", "호이스트", "crane"],
            "CONCRETE": ["콘크리트", "타설", "거푸집", "concrete"],
            "EARTHWORK": ["토공", "굴착", "땅파기", "earthwork"],
            "STEEL": ["철골", "강재", "구조", "steel"],
            "ELECTRICAL": ["전기", "배선", "전력", "electrical"],
            "PLUMBING": ["배관", "상하수도", "급수", "plumbing"]
        }
    
    def build_rules(self, citations: List[Citation]) -> List[RuleItem]:
        """
        Build numeric rules from RAG citations.
        
        Args:
            citations: List of citations from RAG search
            
        Returns:
            List of extracted rules
        """
        rules = []
        
        for citation in citations:
            # Extract rules from each citation
            citation_rules = self._extract_rules_from_citation(citation)
            rules.extend(citation_rules)
        
        # Remove duplicates and save
        unique_rules = self._deduplicate_rules(rules)
        self.rules_store.save_rules(unique_rules)
        
        return unique_rules
    
    def _extract_rules_from_citation(self, citation: Citation) -> List[RuleItem]:
        """Extract rules from a single citation."""
        rules = []
        text = citation.snippet
        
        # Use prompt-based extraction guidance
        try:
            extraction_prompt = get_query_prompt(
                "threshold_builder_extraction",
                text=text
            )
            # For now, we'll use the existing regex-based extraction
            # In a full LLM implementation, this would be used to guide the LLM
        except:
            # Fallback to existing method if prompt not available
            pass
        
        # Extract work type from text
        work_type = self._extract_work_type(text)
        
        # Extract numeric values for different metrics
        for metric, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        value = float(match.group(1))
                        unit = self._get_unit_for_metric(metric)
                        
                        rule = RuleItem(
                            work_type=work_type,
                            metric=metric,
                            value=value,
                            unit=unit,
                            source={
                                "document": citation.document,
                                "page": citation.page,
                                "snippet": citation.snippet
                            },
                            confidence=self._calculate_confidence(citation, pattern),
                            extracted_at=datetime.now(),
                            note=f"Extracted from: {pattern}"
                        )
                        rules.append(rule)
                        
                    except (ValueError, IndexError):
                        continue
        
        # If no numeric rules found, create a note rule
        if not rules:
            rule = RuleItem(
                work_type=work_type,
                metric="general",
                value=None,
                unit="",
                source={
                    "document": citation.document,
                    "page": citation.page,
                    "snippet": citation.snippet
                },
                confidence=0.3,
                extracted_at=datetime.now(),
                note="정량값 없음 - 정성적 기준만 존재"
            )
            rules.append(rule)
        
        return rules
    
    def _extract_work_type(self, text: str) -> str:
        """Extract work type from text."""
        text_lower = text.lower()
        
        for work_type, keywords in self.work_type_mappings.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return work_type
        
        return "GENERAL"
    
    def _get_unit_for_metric(self, metric: str) -> str:
        """Get unit for metric type."""
        units = {
            "wind_speed": "m/s",
            "temperature": "°C",
            "rainfall": "mm",
            "visibility": "m"
        }
        return units.get(metric, "")
    
    def _calculate_confidence(self, citation: Citation, pattern: str) -> float:
        """Calculate confidence score for extracted rule."""
        base_confidence = 0.5
        
        # Adjust based on citation score
        if citation.score:
            base_confidence += citation.score * 0.3
        
        # Adjust based on pattern specificity
        if "이상" in pattern or "이하" in pattern:
            base_confidence += 0.2  # More specific patterns
        
        return min(base_confidence, 1.0)
    
    def _deduplicate_rules(self, rules: List[RuleItem]) -> List[RuleItem]:
        """Remove duplicate rules."""
        seen = set()
        unique_rules = []
        
        for rule in rules:
            # Create a key for deduplication
            key = (rule.work_type, rule.metric, rule.value)
            
            if key not in seen:
                seen.add(key)
                unique_rules.append(rule)
            else:
                # Keep the rule with higher confidence
                for i, existing_rule in enumerate(unique_rules):
                    if (existing_rule.work_type == rule.work_type and 
                        existing_rule.metric == rule.metric and 
                        existing_rule.value == rule.value):
                        if rule.confidence > existing_rule.confidence:
                            unique_rules[i] = rule
                        break
        
        return unique_rules
    
    def get_rules_for_work_type(self, work_type: str) -> List[RuleItem]:
        """Get rules for specific work type."""
        all_rules = self.rules_store.load_rules()
        return [rule for rule in all_rules if rule.work_type == work_type]
    
    def get_rules_for_metric(self, metric: str) -> List[RuleItem]:
        """Get rules for specific metric."""
        all_rules = self.rules_store.load_rules()
        return [rule for rule in all_rules if rule.metric == metric]
    
    def validate_rule(self, rule: RuleItem) -> Dict[str, Any]:
        """Validate a rule for consistency and completeness."""
        validation = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check required fields
        if not rule.work_type:
            validation["errors"].append("Work type is required")
            validation["valid"] = False
        
        if not rule.metric:
            validation["errors"].append("Metric is required")
            validation["valid"] = False
        
        # Check value range
        if rule.value is not None:
            if rule.metric == "wind_speed" and (rule.value < 0 or rule.value > 50):
                validation["warnings"].append("Wind speed value seems unusual")
            
            if rule.metric == "temperature" and (rule.value < -50 or rule.value > 50):
                validation["warnings"].append("Temperature value seems unusual")
        
        # Check confidence
        if rule.confidence < 0.3:
            validation["warnings"].append("Low confidence score")
        
        return validation
    
    def get_system_prompt(self) -> str:
        """Get system prompt for this agent."""
        return get_system_prompt("threshold_builder")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent status and capabilities."""
        return {
            "name": "Threshold Builder Agent",
            "capabilities": [
                "numeric_rule_extraction",
                "work_type_classification",
                "confidence_scoring",
                "rule_deduplication"
            ],
            "supported_metrics": list(self.patterns.keys()),
            "supported_work_types": list(self.work_type_mappings.keys()),
            "system_prompt": self.get_system_prompt()
        }
