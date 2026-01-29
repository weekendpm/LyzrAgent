"""
State schema for document processing workflow using TypedDict.
Defines the complete state structure that flows through all agents.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel


class DocumentInfo(TypedDict):
    """Core document information"""
    id: str
    content: str
    metadata: Dict[str, Any]
    file_type: str
    file_path: Optional[str]
    file_size: Optional[int]
    uploaded_at: datetime


class AgentResult(TypedDict):
    """Standard result structure for each agent"""
    success: bool
    result: Dict[str, Any]
    error: Optional[str]
    confidence_score: Optional[float]
    processing_time: Optional[float]
    timestamp: datetime


class AgentHistoryEntry(TypedDict):
    """Entry in the agent processing history"""
    agent_name: str
    timestamp: datetime
    status: Literal["started", "completed", "failed", "skipped"]
    result: Optional[AgentResult]
    error: Optional[str]


class BusinessRule(TypedDict):
    """Business rule definition"""
    rule_id: str
    rule_name: str
    rule_type: str
    condition: str
    action: str
    priority: int


class AnomalyDetection(TypedDict):
    """Anomaly detection result"""
    anomaly_type: str
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    confidence: float
    affected_fields: List[str]


class HumanReviewRequest(TypedDict):
    """Human review request structure"""
    review_id: str
    reason: str
    priority: Literal["low", "medium", "high", "urgent"]
    required_actions: List[str]
    context: Dict[str, Any]
    assigned_to: Optional[str]
    due_date: Optional[datetime]


class HumanFeedback(TypedDict):
    """Human feedback structure"""
    review_id: str
    reviewer: str
    decision: Literal["approve", "reject", "modify", "escalate"]
    feedback: str
    modifications: Optional[Dict[str, Any]]
    timestamp: datetime


class DocumentProcessingState(TypedDict):
    """
    Complete state for document processing workflow.
    This state flows through all 9 agents and maintains the complete processing context.
    """
    
    # Core document information
    document: DocumentInfo
    
    # Agent processing results
    ingestion_result: Optional[AgentResult]
    classification_result: Optional[AgentResult]
    extraction_result: Optional[AgentResult]
    validation_result: Optional[AgentResult]
    rule_evaluation_result: Optional[AgentResult]
    anomaly_detection_result: Optional[AgentResult]
    human_review_result: Optional[AgentResult]
    audit_learning_result: Optional[AgentResult]
    
    # Workflow control
    current_agent: str
    status: Literal["pending", "processing", "completed", "failed", "requires_human_review", "human_review_pending", "human_review_completed"]
    requires_human_review: bool
    human_feedback: Optional[HumanFeedback]
    
    # Processing history and audit trail
    agent_history: List[AgentHistoryEntry]
    error_log: List[str]
    
    # Business context
    document_type: Optional[str]
    confidence_scores: Dict[str, float]
    business_rules_applied: List[BusinessRule]
    anomalies_detected: List[AnomalyDetection]
    human_review_requests: List[HumanReviewRequest]
    
    # Extracted structured data
    extracted_data: Dict[str, Any]
    validated_data: Dict[str, Any]
    
    # Processing metadata
    workflow_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_processing_time: Optional[float]
    
    # Configuration
    processing_config: Dict[str, Any]
    llm_config: Dict[str, Any]


class WorkflowConfig(BaseModel):
    """Configuration for the document processing workflow"""
    
    # LLM Configuration
    llm_provider: Literal["openai", "anthropic"] = "openai"
    model_name: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 4000
    
    # Processing Configuration
    enable_ocr: bool = True
    enable_human_review: bool = True
    confidence_threshold: float = 0.8
    max_processing_time: int = 300  # seconds
    
    # Business Rules Configuration
    enable_business_rules: bool = True
    enable_anomaly_detection: bool = True
    anomaly_threshold: float = 0.7
    
    # File Processing Configuration
    supported_file_types: List[str] = ["pdf", "docx", "txt", "jpg", "png"]
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    
    # Human Review Configuration
    # Lowered thresholds to reduce false positives for human review
    auto_approve_threshold: float = 0.85
    require_review_threshold: float = 0.4
    escalation_threshold: float = 0.2


def create_initial_state(
    document_id: str,
    content: str,
    file_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[WorkflowConfig] = None
) -> DocumentProcessingState:
    """
    Create initial state for document processing workflow
    
    Args:
        document_id: Unique identifier for the document
        content: Document content (text or file path)
        file_type: Type of file (pdf, docx, txt, etc.)
        metadata: Additional metadata about the document
        config: Workflow configuration
    
    Returns:
        Initial DocumentProcessingState
    """
    now = datetime.now()
    config = config or WorkflowConfig()
    
    return DocumentProcessingState(
        # Document info
        document=DocumentInfo(
            id=document_id,
            content=content,
            metadata=metadata or {},
            file_type=file_type,
            file_path=None,
            file_size=None,
            uploaded_at=now
        ),
        
        # Agent results (all None initially)
        # For direct text processing, simulate successful ingestion
        ingestion_result={
            "success": True,
            "content_extracted": True,
            "content_length": len(content),
            "processing_time": 0.001,
            "metadata_extracted": metadata or {},
            "confidence": 1.0,
            "message": "Direct text input - ingestion simulated"
        } if content else None,
        classification_result=None,
        extraction_result=None,
        validation_result=None,
        rule_evaluation_result=None,
        anomaly_detection_result=None,
        human_review_result=None,
        audit_learning_result=None,
        
        # Workflow control
        current_agent="ingestion",
        status="pending",
        requires_human_review=False,
        human_feedback=None,
        
        # Processing history
        agent_history=[],
        error_log=[],
        
        # Business context
        document_type=None,
        confidence_scores={},
        business_rules_applied=[],
        anomalies_detected=[],
        human_review_requests=[],
        
        # Data
        extracted_data={},
        validated_data={},
        
        # Metadata
        workflow_id=f"workflow_{document_id}_{int(now.timestamp())}",
        started_at=now,
        completed_at=None,
        total_processing_time=None,
        
        # Configuration
        processing_config=config.dict(),
        llm_config={
            "provider": config.llm_provider,
            "model": config.model_name,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
    )


def add_agent_history_entry(
    state: DocumentProcessingState,
    agent_name: str,
    status: Literal["started", "completed", "failed", "skipped"],
    result: Optional[AgentResult] = None,
    error: Optional[str] = None
) -> DocumentProcessingState:
    """
    Add an entry to the agent processing history
    
    Args:
        state: Current state
        agent_name: Name of the agent
        status: Processing status
        result: Agent result (if completed)
        error: Error message (if failed)
    
    Returns:
        Updated state with new history entry
    """
    entry = AgentHistoryEntry(
        agent_name=agent_name,
        timestamp=datetime.now(),
        status=status,
        result=result,
        error=error
    )
    
    state["agent_history"].append(entry)
    return state


def update_agent_result(
    state: DocumentProcessingState,
    agent_name: str,
    result: AgentResult
) -> DocumentProcessingState:
    """
    Update the result for a specific agent
    
    Args:
        state: Current state
        agent_name: Name of the agent
        result: Agent processing result
    
    Returns:
        Updated state with agent result
    """
    result_key = f"{agent_name}_result"
    if result_key in state:
        state[result_key] = result
    
    # Update confidence scores
    if result.get("confidence_score"):
        state["confidence_scores"][agent_name] = result["confidence_score"]
    
    return state