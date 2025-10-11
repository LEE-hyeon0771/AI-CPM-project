"""
CPM (Critical Path Method) calculation service.
"""
from typing import List, Dict, Any, Tuple, Set
from datetime import date, timedelta
from ...schemas.io import WBSItem


class CPMService:
    """Critical Path Method calculation service."""
    
    def __init__(self):
        pass
    
    def compute_cpm(self, wbs_items: List[WBSItem], start_date: date = None) -> Dict[str, Any]:
        """
        Compute CPM schedule for WBS items.
        
        Args:
            wbs_items: List of WBS items
            start_date: Project start date
            
        Returns:
            CPM calculation results
        """
        if not wbs_items:
            return {"tasks": [], "critical_path": [], "project_duration": 0}
        
        if start_date is None:
            start_date = date.today()
        
        # Create task dictionary
        tasks = {item.id: item for item in wbs_items}
        
        # Calculate forward pass (ES, EF)
        forward_results = self._forward_pass(tasks, start_date)
        
        # Calculate backward pass (LS, LF)
        backward_results = self._backward_pass(tasks, forward_results)
        
        # Calculate total float and identify critical path
        critical_path = self._find_critical_path(tasks, forward_results, backward_results)
        
        # Format results
        results = {
            "tasks": [],
            "critical_path": critical_path,
            "project_duration": max([r["ef"] for r in forward_results.values()]),
            "start_date": start_date.isoformat()
        }
        
        for task_id in tasks:
            task_result = {
                "id": task_id,
                "name": tasks[task_id].name,
                "duration": tasks[task_id].duration,
                "work_type": tasks[task_id].work_type,
                "es": forward_results[task_id]["es"],
                "ef": forward_results[task_id]["ef"],
                "ls": backward_results[task_id]["ls"],
                "lf": backward_results[task_id]["lf"],
                "tf": backward_results[task_id]["tf"],
                "is_critical": task_id in critical_path,
                "predecessors": tasks[task_id].predecessors
            }
            results["tasks"].append(task_result)
        
        return results
    
    def _forward_pass(self, tasks: Dict[str, WBSItem], start_date: date) -> Dict[str, Dict[str, int]]:
        """Calculate early start and early finish times."""
        results = {}
        visited = set()
        
        def calculate_es_ef(task_id: str) -> Tuple[int, int]:
            if task_id in results:
                return results[task_id]["es"], results[task_id]["ef"]
            
            if task_id in visited:
                # Circular dependency - return 0
                return 0, 0
            
            visited.add(task_id)
            task = tasks[task_id]
            
            # Calculate ES based on predecessors
            es = 0
            for pred in task.predecessors:
                pred_id = pred["id"]
                if pred_id in tasks:
                    pred_es, pred_ef = calculate_es_ef(pred_id)
                    
                    if pred["type"] == "FS":  # Finish-to-Start
                        es = max(es, pred_ef + pred["lag"])
                    elif pred["type"] == "SS":  # Start-to-Start
                        es = max(es, pred_es + pred["lag"])
                    elif pred["type"] == "FF":  # Finish-to-Finish
                        es = max(es, pred_ef - task.duration + pred["lag"])
                    elif pred["type"] == "SF":  # Start-to-Finish
                        es = max(es, pred_es - task.duration + pred["lag"])
            
            ef = es + task.duration
            
            results[task_id] = {"es": es, "ef": ef}
            visited.remove(task_id)
            
            return es, ef
        
        # Calculate for all tasks
        for task_id in tasks:
            calculate_es_ef(task_id)
        
        return results
    
    def _backward_pass(self, tasks: Dict[str, WBSItem], forward_results: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
        """Calculate late start and late finish times."""
        results = {}
        
        # Find project end time
        project_end = max([r["ef"] for r in forward_results.values()])
        
        # Initialize all tasks
        for task_id in tasks:
            results[task_id] = {"ls": 0, "lf": 0, "tf": 0}
        
        # Calculate LF and LS for each task
        for task_id in tasks:
            task = tasks[task_id]
            
            # Find successors
            successors = []
            for other_id, other_task in tasks.items():
                for pred in other_task.predecessors:
                    if pred["id"] == task_id:
                        successors.append((other_id, pred))
            
            if not successors:
                # No successors - LF = project end
                results[task_id]["lf"] = project_end
            else:
                # LF = minimum LS of successors
                min_ls = float('inf')
                for succ_id, pred_rel in successors:
                    succ_es = forward_results[succ_id]["es"]
                    
                    if pred_rel["type"] == "FS":
                        min_ls = min(min_ls, succ_es - pred_rel["lag"])
                    elif pred_rel["type"] == "SS":
                        min_ls = min(min_ls, succ_es - pred_rel["lag"])
                    elif pred_rel["type"] == "FF":
                        min_ls = min(min_ls, succ_es + tasks[succ_id].duration - pred_rel["lag"])
                    elif pred_rel["type"] == "SF":
                        min_ls = min(min_ls, succ_es + tasks[succ_id].duration - pred_rel["lag"])
                
                results[task_id]["lf"] = min_ls if min_ls != float('inf') else project_end
            
            # LS = LF - duration
            results[task_id]["ls"] = results[task_id]["lf"] - task.duration
            
            # TF = LS - ES
            results[task_id]["tf"] = results[task_id]["ls"] - forward_results[task_id]["es"]
        
        return results
    
    def _find_critical_path(self, tasks: Dict[str, WBSItem], forward_results: Dict[str, Dict[str, int]], backward_results: Dict[str, Dict[str, int]]) -> List[str]:
        """Find the critical path."""
        critical_path = []
        
        # Find tasks with zero total float
        critical_tasks = []
        for task_id in tasks:
            if backward_results[task_id]["tf"] == 0:
                critical_tasks.append(task_id)
        
        # Sort critical tasks by ES
        critical_tasks.sort(key=lambda x: forward_results[x]["es"])
        
        # Build critical path by following dependencies
        visited = set()
        
        def build_path(task_id: str):
            if task_id in visited:
                return
            
            visited.add(task_id)
            critical_path.append(task_id)
            
            # Find critical successors
            for other_id, other_task in tasks.items():
                if other_id in critical_tasks and other_id not in visited:
                    for pred in other_task.predecessors:
                        if pred["id"] == task_id and backward_results[other_id]["tf"] == 0:
                            build_path(other_id)
                            break
        
        # Start with the first critical task
        if critical_tasks:
            build_path(critical_tasks[0])
        
        return critical_path
    
    def calculate_delays(self, ideal_schedule: Dict[str, Any], delay_days: int) -> Dict[str, Any]:
        """Calculate impact of delays on the schedule."""
        if delay_days <= 0:
            return {
                "new_duration": ideal_schedule["project_duration"],
                "affected_tasks": [],
                "new_critical_path": ideal_schedule["critical_path"]
            }
        
        # Simple delay calculation - add to project duration
        new_duration = ideal_schedule["project_duration"] + delay_days
        
        # Find tasks that might be affected
        affected_tasks = []
        for task in ideal_schedule["tasks"]:
            if task["is_critical"]:
                affected_tasks.append({
                    "id": task["id"],
                    "name": task["name"],
                    "original_ef": task["ef"],
                    "new_ef": task["ef"] + delay_days,
                    "delay": delay_days
                })
        
        return {
            "new_duration": new_duration,
            "affected_tasks": affected_tasks,
            "new_critical_path": ideal_schedule["critical_path"]  # Critical path remains the same
        }
