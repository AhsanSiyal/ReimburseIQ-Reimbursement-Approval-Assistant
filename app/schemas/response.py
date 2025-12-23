from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

Decision = Literal["APPROVE_RECOMMENDED", "REJECT_RECOMMENDED", "NEEDS_MORE_INFO"]

class Issue(BaseModel):
    code: str
    message: str
    rule_ids: List[str] = Field(default_factory=list)

class LineResult(BaseModel):
    line_id: str
    status: Literal["COMPLIANT", "NON_COMPLIANT"]
    issues: List[Issue] = Field(default_factory=list)
    suggested_fix: Optional[str] = None

class Citation(BaseModel):
    rule_id: str
    section_title: Optional[str] = None
    source_path: Optional[str] = None
    snippet: str

class EvaluateResponse(BaseModel):
    decision: Decision
    summary: str
    approval_route: List[str]
    claim_total: float

    lines: List[LineResult]
    missing_info: List[str] = Field(default_factory=list)

    citations: List[Citation] = Field(default_factory=list)
    debug: Optional[Dict[str, Any]] = None
