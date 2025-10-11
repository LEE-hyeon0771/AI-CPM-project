"""
Rules store for persisting and loading extracted rules.
"""
import json
import os
from typing import List, Dict, Any
from datetime import datetime
from ...schemas.io import RuleItem
from ...config import get_settings


class RulesStore:
    """Store for managing extracted rules."""
    
    def __init__(self, rules_path: str = None):
        self.settings = get_settings()
        self.rules_path = rules_path or "./data/rules/rules.jsonl"
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self):
        """Ensure the rules directory exists."""
        os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
    
    def save_rules(self, rules: List[RuleItem]) -> None:
        """
        Save rules to JSONL file.
        
        Args:
            rules: List of rules to save
        """
        try:
            with open(self.rules_path, 'w', encoding='utf-8') as f:
                for rule in rules:
                    # Convert RuleItem to dict
                    rule_dict = {
                        "work_type": rule.work_type,
                        "metric": rule.metric,
                        "value": rule.value,
                        "unit": rule.unit,
                        "source": rule.source,
                        "confidence": rule.confidence,
                        "extracted_at": rule.extracted_at.isoformat(),
                        "note": rule.note
                    }
                    f.write(json.dumps(rule_dict, ensure_ascii=False) + '\n')
            
            print(f"Saved {len(rules)} rules to {self.rules_path}")
            
        except Exception as e:
            print(f"Error saving rules: {e}")
            raise
    
    def load_rules(self) -> List[RuleItem]:
        """
        Load rules from JSONL file.
        
        Returns:
            List of loaded rules
        """
        rules = []
        
        if not os.path.exists(self.rules_path):
            return rules
        
        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        rule_dict = json.loads(line)
                        
                        # Convert back to RuleItem
                        rule = RuleItem(
                            work_type=rule_dict.get("work_type", ""),
                            metric=rule_dict.get("metric", ""),
                            value=rule_dict.get("value"),
                            unit=rule_dict.get("unit", ""),
                            source=rule_dict.get("source", {}),
                            confidence=rule_dict.get("confidence", 0.0),
                            extracted_at=datetime.fromisoformat(rule_dict.get("extracted_at", datetime.now().isoformat())),
                            note=rule_dict.get("note")
                        )
                        rules.append(rule)
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Error parsing rule line: {e}")
                        continue
            
            print(f"Loaded {len(rules)} rules from {self.rules_path}")
            
        except Exception as e:
            print(f"Error loading rules: {e}")
            return []
        
        return rules
    
    def append_rules(self, new_rules: List[RuleItem]) -> None:
        """
        Append new rules to existing file.
        
        Args:
            new_rules: New rules to append
        """
        try:
            with open(self.rules_path, 'a', encoding='utf-8') as f:
                for rule in new_rules:
                    rule_dict = {
                        "work_type": rule.work_type,
                        "metric": rule.metric,
                        "value": rule.value,
                        "unit": rule.unit,
                        "source": rule.source,
                        "confidence": rule.confidence,
                        "extracted_at": rule.extracted_at.isoformat(),
                        "note": rule.note
                    }
                    f.write(json.dumps(rule_dict, ensure_ascii=False) + '\n')
            
            print(f"Appended {len(new_rules)} rules to {self.rules_path}")
            
        except Exception as e:
            print(f"Error appending rules: {e}")
            raise
    
    def clear_rules(self) -> None:
        """Clear all rules from the store."""
        try:
            if os.path.exists(self.rules_path):
                os.remove(self.rules_path)
            print("Cleared all rules")
        except Exception as e:
            print(f"Error clearing rules: {e}")
            raise
    
    def get_rules_by_work_type(self, work_type: str) -> List[RuleItem]:
        """Get rules for specific work type."""
        all_rules = self.load_rules()
        return [rule for rule in all_rules if rule.work_type == work_type]
    
    def get_rules_by_metric(self, metric: str) -> List[RuleItem]:
        """Get rules for specific metric."""
        all_rules = self.load_rules()
        return [rule for rule in all_rules if rule.metric == metric]
    
    def get_rules_stats(self) -> Dict[str, Any]:
        """Get statistics about stored rules."""
        rules = self.load_rules()
        
        stats = {
            "total_rules": len(rules),
            "work_types": {},
            "metrics": {},
            "confidence_distribution": {
                "high": 0,  # > 0.7
                "medium": 0,  # 0.4 - 0.7
                "low": 0  # < 0.4
            }
        }
        
        for rule in rules:
            # Count by work type
            if rule.work_type not in stats["work_types"]:
                stats["work_types"][rule.work_type] = 0
            stats["work_types"][rule.work_type] += 1
            
            # Count by metric
            if rule.metric not in stats["metrics"]:
                stats["metrics"][rule.metric] = 0
            stats["metrics"][rule.metric] += 1
            
            # Count by confidence
            if rule.confidence > 0.7:
                stats["confidence_distribution"]["high"] += 1
            elif rule.confidence >= 0.4:
                stats["confidence_distribution"]["medium"] += 1
            else:
                stats["confidence_distribution"]["low"] += 1
        
        return stats
