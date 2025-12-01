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
    # frontend에서 의도적으로 특정 모드를 지정할 수 있도록 하는 선택적 필드
    # 예: "law_only" → 법규 전용 Q&A 화면에서 사용
    mode: Optional[str] = None


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