"""
Pydantic models for data validation and serialization
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class BacklogItem(BaseModel):
    """Raw backlog item from Excel sheet"""
    tag: str = Field(alias="Tag")
    item_class: Optional[str] = Field(None, alias="Item Class")
    description: Optional[str] = Field(None, alias="Description")
    functional_location: Optional[str] = Field(None, alias="Functional Location")
    last_insp: Optional[str] = Field(None, alias="Last Insp/")
    freq: Optional[str] = Field(None, alias="Freq/ (SAP)")
    next_insp: Optional[str] = Field(None, alias="Next Insp/")
    year: Optional[str] = Field(None, alias="Year")
    due_date: Optional[str] = Field(None, alias="Due Date")
    compl_date: Optional[str] = Field(None, alias="Compl/ date")
    pmonth_insp: Optional[str] = Field(None, alias="PMonth Insp")
    cmonth_insp: Optional[str] = Field(None, alias="CMonth Insp")
    sece_status: Optional[str] = Field(None, alias="SECE STATUS")
    delay: Optional[str] = Field(None, alias="Delay")
    m_item: Optional[str] = Field(None, alias="M. Item")
    m_plan: Optional[str] = Field(None, alias="M. Plan")
    job_done: Optional[str] = Field(None, alias="Job Done")
    days_in_backlog: int = Field(0, alias="Days in Backlog")
    backlog: str = Field(alias="Backlog?")
    sece: bool = Field(False, alias="SECE")
    system: str = Field(alias="System")
    location: str = Field(alias="Location")
    
    class Config:
        populate_by_name = True


class DashboardItem(BaseModel):
    """Processed dashboard item for frontend display"""
    tag_id: str = Field(..., alias="Tag ID")
    category: str = Field('Uncategorized', alias="Category")
    description: str = Field(..., max_length=100)
    system: str
    location: str
    due_date: str = Field(..., alias="Due Date")
    days_overdue: int = Field(..., alias="Days Overdue", ge=0)
    sece: str = Field(..., alias="SECE")
    status: str
    action: str
    risk_level: str = Field(..., alias="Risk Level")
    color: str
    
    @validator('risk_level')
    def validate_risk_level(cls, v):
        allowed = ['High', 'Medium', 'Low']
        if v not in allowed:
            raise ValueError(f'Risk level must be one of: {allowed}')
        return v
    
    @validator('sece')
    def validate_sece(cls, v):
        allowed = ['Yes', 'No']
        if v not in allowed:
            return 'No'
        return v
    
    class Config:
        populate_by_name = True


class DashboardData(BaseModel):
    """Dashboard data container"""
    backlog: List[Dict[str, Any]]
    performance: List[Dict[str, Any]]
    pending: List[Dict[str, Any]] = []
    sow_progress: Optional[Dict[str, Any]] = None


class StatusUpdate(BaseModel):
    """User-entered status update for a tag"""
    tag_id: str
    new_status: str
    note: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class StatusHistory(BaseModel):
    """All status updates for a tag"""
    tag_id: str
    history: List[StatusUpdate] = []


class ProcessResponse(BaseModel):
    """API response model"""
    success: bool
    message: str
    items_processed: int
    dashboard: DashboardData
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's question or message")
    discipline: Optional[str] = Field(None, description="Specific discipline agent to chat with (null for all agents)")
    site: Optional[str] = Field(None, description="Site identifier for context")
    items: Optional[List[Dict[str, Any]]] = Field(None, description="Raw inspection items for RAG (sent from frontend)")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    model_id: Optional[str] = Field(None, description="Model catalogue key, e.g. 'openrouter/minimax/mm-m2'")
    stream: bool = Field(False, description="Enable Server-Sent Events (SSE) streaming for token-by-token responses")


class InspectionRecord(BaseModel):
    """Inspection history record"""
    id: Optional[int] = None
    tag_id: str
    inspection_date: Optional[str] = None
    inspection_type: Optional[str] = None
    result: Optional[str] = None
    inspector: Optional[str] = None
    notes: Optional[str] = None
    timestamp: Optional[datetime] = None


class EquipmentMaster(BaseModel):
    """Equipment master data (SAP-like)"""
    tag_id: str
    functional_location: Optional[str] = None
    equipment_category: Optional[str] = None
    description: Optional[str] = None
    system: Optional[str] = None
    location: Optional[str] = None
    manufacturing_details: Optional[str] = None
    fluid_service: Optional[str] = None
    backlog_tracker: Optional[str] = None
    inspections_done: Optional[str] = None
    history_comments: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class ChatFeedbackRequest(BaseModel):
    """Thumbs up/down feedback on a chat response"""
    message_id: str = Field(..., description="Unique ID of the agent message")
    query: str = Field(..., description="The user's original question")
    response: str = Field(..., description="The agent's response text")
    rating: int = Field(..., description="1 for thumbs up, -1 for thumbs down")
    comment: Optional[str] = Field(None, description="Optional user comment")
    discipline: Optional[str] = Field(None, description="Discipline agent used")
    model_id: Optional[str] = Field(None, description="Model catalogue key")
    site: Optional[str] = Field(None, description="Site context")


class EquipmentDetail(BaseModel):
    """Complete equipment detail with history"""
    equipment: EquipmentMaster
    inspection_history: List[InspectionRecord] = []
    status_history: List[StatusUpdate] = []
