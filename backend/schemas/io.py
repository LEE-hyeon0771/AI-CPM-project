"""
Request and response models for the API.
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel


# Request Models
class ContractSetupRequest(BaseModel):
    """Contract setup request model."""
    contract_amount: float
    ld_rate: float
    indirect_cost_per_day: float
    start_date: date
    calendar_policy: str = "5d"


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    wbs_text: Optional[str] = None


# Response Models
class Citation(BaseModel):
    """Citation model for RAG results."""
    document: str
    page: int
    snippet: str
    score: Optional[float] = None


class WBSItem(BaseModel):
    """WBS item model."""
    id: str
    name: str
    duration: int
    predecessors: List[Dict[str, Any]] = []
    work_type: str


class CPMResult(BaseModel):
    """CPM calculation result."""
    es: int
    ef: int
    ls: int
    lf: int
    tf: int
    is_critical: bool


class DelayRow(BaseModel):
    """Delay analysis row."""
    date: date
    reason: str
    affected: List[str]
    day_delay: int
    cumulative: int


class CostSummary(BaseModel):
    """Cost analysis summary."""
    indirect_cost: float
    ld: float
    total: float


class UITable(BaseModel):
    """UI table model."""
    title: str
    headers: List[str]
    rows: List[List[Union[str, int, float]]]


class UICard(BaseModel):
    """UI card model."""
    title: str
    value: str
    subtitle: Optional[str] = None


class UIResponse(BaseModel):
    """UI response model."""
    tables: List[UITable] = []
    cards: List[UICard] = []


class ChatResponse(BaseModel):
    """Chat response model."""
    ideal_schedule: Dict[str, Any]
    delay_table: Dict[str, Any]
    cost_summary: CostSummary
    citations: List[Citation] = []
    ui: UIResponse


class RuleItem(BaseModel):
    """Rule item model."""
    work_type: str
    metric: str
    value: Optional[float] = None
    unit: str
    source: Dict[str, Any]
    confidence: float
    extracted_at: datetime
    note: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None