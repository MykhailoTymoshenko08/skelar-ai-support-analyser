from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from enum import Enum

class IntentEnum(str, Enum):
    PAYMENT_PROBLEM = "payment_problem"
    TECH_ERROR = "tech_error"
    ACCOUNT_ACCESS = "account_access"
    TARIFF = "tariff"
    REFUND = "refund"
    OTHER = "other"

class SatisfactionEnum(str, Enum):
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    DISSATISFIED = "dissatisfied"
    HIDDEN_DISSATISFACTION = "hidden_dissatisfaction"

class AgentMistakeEnum(str, Enum):
    IGNORED_QUESTION = "ignored_question"
    INCORRECT_INFO = "incorrect_info"
    RUDE_TONE = "rude_tone"
    NO_RESOLUTION = "no_resolution"
    UNNECESSARY_ESCALATION = "unnecessary_escalation"
    INCOMPLETE_INFO = "incomplete_info"
    TECH_JARGON = "tech_jargon"
    IMPATIENT = "impatient"

class ConversationTurn(BaseModel):
    role: str 
    content: str
    timestamp: Optional[int] = None

class Conversation(BaseModel):
    id: int
    intent: IntentEnum
    client_persona: str
    turns: List[ConversationTurn]
    metadata: dict = Field(default_factory=dict)

class AnalysisResult(BaseModel):
    conversation_id: int
    
    intent: IntentEnum
    satisfaction: SatisfactionEnum
    quality_score: int = Field(ge=1, le=5, description="Оцінка якості від 1 до 5")
    agent_mistakes: List[str] = Field(default_factory=list)  
    
    resolution_status: str  
    hidden_dissatisfaction_score: float = Field(ge=0.0, le=1.0, default=0.0)
    key_action_items: List[str] = Field(default_factory=list)
    agent_performance: str  
    detected_persona: str
    
    
    @field_validator('quality_score')
    def validate_quality_score(cls, v):
        if v < 1 or v > 5:
            raise ValueError('quality_score must be between 1 and 5')
        return v
    
    @field_validator('hidden_dissatisfaction_score')
    def validate_hidden_score(cls, v):
        if v < 0 or v > 1:
            raise ValueError('hidden_dissatisfaction_score must be between 0 and 1')
        return v

class AnalysisResults(BaseModel):
    results: List[AnalysisResult]
    metadata: dict = Field(default_factory=dict)