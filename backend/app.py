"""
FastAPI application for Smart Construction Scheduling & Economic Analysis.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
import uvicorn

from .config import get_settings
from .supervisor import Supervisor
from .schemas.io import (
    ContractSetupRequest, ChatRequest, ChatResponse, 
    ErrorResponse, RuleItem
)
from .tools.services.wbs_parser import WBSParser
from .agents.law_rag import LawRAGAgent
from .agents.threshold_builder import ThresholdBuilderAgent
from .agents.cpm_weather_cost import CPMWeatherCostAgent
from .agents.merger import MergerAgent
from .tools.rules.store import RulesStore

# Initialize FastAPI app
app = FastAPI(
    title="Smart Construction Scheduling & Economic Analysis",
    description="Multi-agent system for construction project management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (in production, use proper state management)
contract_data: Dict[str, Any] = {}
supervisor = Supervisor()
wbs_parser = WBSParser()
law_rag_agent = LawRAGAgent()
threshold_builder = ThresholdBuilderAgent()
cpm_weather_cost_agent = CPMWeatherCostAgent()
merger_agent = MergerAgent()
rules_store = RulesStore()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Smart Construction Scheduling & Economic Analysis API"}


@app.post("/api/setup/contract", response_model=Dict[str, str])
async def setup_contract(request: ContractSetupRequest):
    """Setup contract parameters."""
    try:
        global contract_data
        contract_data = {
            "contract_amount": request.contract_amount,
            "ld_rate": request.ld_rate,
            "indirect_cost_per_day": request.indirect_cost_per_day,
            "start_date": request.start_date.isoformat(),
            "calendar_policy": request.calendar_policy
        }
        return {"status": "success", "message": "Contract parameters set successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint for project analysis."""
    try:
        # Route intent
        routing = supervisor.route_intent(request.message)
        
        # Parse WBS if provided
        wbs_json = None
        if supervisor.should_parse_wbs(request.wbs_text):
            wbs_json = wbs_parser.parse_wbs(request.wbs_text)
        
        # Execute required agents
        results = {}
        
        if "law_rag" in routing["required_agents"]:
            work_types = supervisor.extract_work_types(request.wbs_text or "")
            results["law_rag"] = law_rag_agent.search_regulations(
                request.message, work_types
            )
        
        if "threshold_builder" in routing["required_agents"]:
            if "law_rag" in results:
                results["threshold_builder"] = threshold_builder.build_rules(
                    results["law_rag"]
                )
        
        if "cpm_weather_cost" in routing["required_agents"]:
            results["cpm_weather_cost"] = cpm_weather_cost_agent.analyze(
                wbs_json, contract_data, results.get("threshold_builder", [])
            )
        
        # Merge results
        if "merger" in routing["required_agents"]:
            final_result = merger_agent.merge_results(results, contract_data)
            return final_result
        
        # Fallback response
        return ChatResponse(
            ideal_schedule={},
            delay_table={},
            cost_summary={"indirect_cost": 0, "ld": 0, "total": 0},
            citations=[],
            ui={"tables": [], "cards": []}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules/refresh", response_model=Dict[str, Any])
async def refresh_rules():
    """Refresh rules from RAG snippets."""
    try:
        # Search for general construction regulations
        law_results = law_rag_agent.search_regulations("건설 안전 기준", [])
        
        # Build rules from results
        rules = threshold_builder.build_rules(law_results)
        
        # Store rules
        rules_store.save_rules(rules)
        
        return {
            "status": "success",
            "rules_count": len(rules),
            "message": f"Successfully refreshed {len(rules)} rules"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/rules", response_model=Dict[str, Any])
async def get_rules():
    """Get current rules."""
    try:
        rules = rules_store.load_rules()
        return {
            "status": "success",
            "rules": rules,
            "count": len(rules)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "faiss_available": settings.faiss_index_path,
        "use_stub": settings.use_stub
    }


@app.get("/api/prompts")
async def get_available_prompts():
    """Get list of available prompts."""
    from .utils.prompt_loader import prompt_loader
    try:
        prompts = prompt_loader.get_available_prompts()
        return {
            "status": "success",
            "prompts": prompts,
            "count": len(prompts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prompts/{prompt_name}")
async def get_prompt(prompt_name: str):
    """Get specific prompt content."""
    from .utils.prompt_loader import get_prompt
    try:
        content = get_prompt(prompt_name)
        return {
            "status": "success",
            "prompt_name": prompt_name,
            "content": content
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/status")
async def get_agents_status():
    """Get status of all agents."""
    try:
        return {
            "status": "success",
            "agents": {
                "supervisor": supervisor.get_system_prompt(),
                "law_rag": law_rag_agent.get_agent_status(),
                "threshold_builder": threshold_builder.get_agent_status(),
                "cpm_weather_cost": cpm_weather_cost_agent.get_agent_status(),
                "merger": merger_agent.get_agent_status()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
