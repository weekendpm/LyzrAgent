"""
FastAPI application for document processing platform.
Provides REST API and WebSocket endpoints for the document processing workflow.
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
import uvicorn

# Import workflow components
from workflows.document_workflow import get_workflow, DocumentProcessingWorkflow
from workflows.state_schema import WorkflowConfig, HumanFeedback
from api.websocket_manager import WebSocketManager

# LangSmith tracing imports
try:
    from langsmith import traceable
    from langchain.callbacks import LangChainTracer
    LANGSMITH_AVAILABLE = True
except ImportError:
    # Fallback if LangSmith is not available
    def traceable(name=None):
        def decorator(func):
            return func
        return decorator
    LANGSMITH_AVAILABLE = False

# Configure LangSmith tracing
import os
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGSMITH_TRACING", "true")
os.environ.setdefault("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
os.environ.setdefault("LANGCHAIN_PROJECT", "pr-frosty-cloakroom-13")
os.environ.setdefault("LANGSMITH_PROJECT", "pr-frosty-cloakroom-13")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Document Processing Platform",
    description="Advanced document processing with AI agents and human-in-the-loop capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware - Production ready
def get_cors_origins():
    """Get CORS origins for production and Lovable integration"""
    if os.environ.get("ENVIRONMENT") == "production":
        return [
            "https://*.lovable.dev",  # Lovable preview URLs
            "https://*.lovableproject.com",  # Lovable production URLs
            "https://lovable.dev",  # Lovable main domain
            # Add your client's domains here
        ]
    else:
        return [
            "http://localhost:3000",  # Local development
            "https://*.lovable.dev",  # Lovable preview URLs
            "https://*.lovableproject.com",  # Lovable production URLs
            "https://lovable.dev",  # Lovable main domain
            "*"  # Allow all for development
        ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Initialize WebSocket manager
websocket_manager = WebSocketManager()

# Global workflow instance
workflow_instance: Optional[DocumentProcessingWorkflow] = None


# Pydantic models for API
class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: str
    workflow_id: str
    thread_id: str
    message: str
    status: str
    requires_human_review: bool = False


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    document_id: str
    current_status: str
    current_agent: Optional[str]
    next_agent: Optional[str]
    progress: Dict[str, Any]
    timing: Dict[str, Any]
    human_interaction: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    is_complete: bool
    can_continue: bool


class HumanReviewRequest(BaseModel):
    decision: str = Field(..., description="approve, reject, modify, or escalate")
    feedback: str = Field(..., description="Human feedback text")
    reviewer: str = Field(..., description="Reviewer identifier")
    modifications: Optional[Dict[str, Any]] = Field(None, description="Data modifications if decision is 'modify'")


class ProcessingResultResponse(BaseModel):
    success: bool
    document_id: str
    workflow_id: str
    status: str
    extracted_data: Dict[str, Any]
    validated_data: Dict[str, Any]
    business_rules_applied: List[Dict[str, Any]]
    anomalies_detected: List[Dict[str, Any]]
    human_review_required: bool
    processing_time: float
    confidence_scores: Dict[str, float]

class SimpleStatusResponse(BaseModel):
    """Simplified status response for Lovable frontend"""
    document_id: str
    status: str
    progress_percentage: float
    current_step: str
    is_complete: bool
    requires_human_review: bool
    error: Optional[str] = None


# Dependency to get workflow instance
def get_workflow_instance() -> DocumentProcessingWorkflow:
    global workflow_instance
    if workflow_instance is None:
        config = WorkflowConfig()
        workflow_instance = get_workflow(config)
    return workflow_instance


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Document Processing Platform API")
    
    # Initialize workflow
    global workflow_instance
    config = WorkflowConfig()
    workflow_instance = get_workflow(config)
    
    # Create upload directory
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    logger.info("Document Processing Platform API started successfully")


# Root endpoint for Lovable
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Document Processing Platform API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "process_document": "/process-document",
            "process_text": "/process-text",
            "status": "/status/{thread_id}",
            "results": "/results/{thread_id}",
            "websocket": "/workflow/{document_id}/stream"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Document Processing Platform"
    }


# Document processing endpoints
@app.post("/process-document", response_model=DocumentUploadResponse)
async def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Upload and process a document through the complete workflow
    
    Args:
        file: Uploaded file
        workflow: Workflow instance
    
    Returns:
        Processing initiation response
    """
    try:
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Get file extension
        file_extension = file.filename.split('.')[-1].lower()
        supported_types = ['pdf', 'docx', 'txt', 'jpg', 'jpeg', 'png']
        
        if file_extension not in supported_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_extension}. Supported types: {supported_types}"
            )
        
        # Save uploaded file
        upload_dir = "uploads"
        file_path = os.path.join(upload_dir, f"{document_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Start processing in background
        background_tasks.add_task(
            process_document_background,
            document_id=document_id,
            file_path=file_path,
            file_type=file_extension,
            original_filename=file.filename,
            workflow=workflow
        )
        
        return DocumentUploadResponse(
            success=True,
            document_id=document_id,
            workflow_id=f"workflow_{document_id}",
            thread_id=f"thread_{document_id}_{int(datetime.now().timestamp())}",
            message="Document uploaded successfully. Processing started.",
            status="processing",
            requires_human_review=False
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@app.post("/process-text")
async def process_text(
    background_tasks: BackgroundTasks,
    text_content: str,
    document_type: str = "txt",
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Process text content directly without file upload
    
    Args:
        text_content: Text content to process
        document_type: Type of document (default: txt)
        workflow: Workflow instance
    
    Returns:
        Processing initiation response
    """
    try:
        if not text_content.strip():
            raise HTTPException(status_code=400, detail="No text content provided")
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Start processing in background
        background_tasks.add_task(
            process_text_background,
            document_id=document_id,
            content=text_content,
            file_type=document_type,
            workflow=workflow
        )
        
        return DocumentUploadResponse(
            success=True,
            document_id=document_id,
            workflow_id=f"workflow_{document_id}",
            thread_id=f"thread_{document_id}_{int(datetime.now().timestamp())}",
            message="Text processing started.",
            status="processing",
            requires_human_review=False
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Text processing failed: {str(e)}")


# Status and monitoring endpoints
@app.get("/status/{thread_id}", response_model=WorkflowStatusResponse)
async def get_document_status(
    thread_id: str,
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Get current processing status of a document
    
    Args:
        thread_id: Thread identifier (full thread ID with timestamp)
        workflow: Workflow instance
    
    Returns:
        Current workflow status
    """
    try:
        state = await workflow.get_workflow_state(thread_id)
        
        if not state:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        
        from agents.coordinator_agent import get_workflow_status
        status_info = get_workflow_status(state)
        
        return WorkflowStatusResponse(**status_info)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document status: {str(e)}")


@app.get("/results/{thread_id}", response_model=ProcessingResultResponse)
async def get_processing_results(
    thread_id: str,
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Get final processing results for a completed document
    
    Args:
        thread_id: Thread identifier (full thread ID with timestamp)
        workflow: Workflow instance
    
    Returns:
        Complete processing results
    """
    try:
        state = await workflow.get_workflow_state(thread_id)
        
        if not state:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        
        # Calculate total processing time
        total_time = 0
        if state.get("completed_at") and state.get("started_at"):
            total_time = (state["completed_at"] - state["started_at"]).total_seconds()
        
        return ProcessingResultResponse(
            success=state.get("status") in ["completed", "human_review_completed"],
            document_id=state["document"]["id"],
            workflow_id=state.get("workflow_id", ""),
            status=state.get("status", "unknown"),
            extracted_data=state.get("extracted_data", {}),
            validated_data=state.get("validated_data", {}),
            business_rules_applied=state.get("business_rules_applied", []),
            anomalies_detected=state.get("anomalies_detected", []),
            human_review_required=state.get("requires_human_review", False),
            processing_time=total_time,
            confidence_scores=state.get("confidence_scores", {})
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get results for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing results: {str(e)}")


# Human review endpoints
@app.post("/human-review/{thread_id}/submit")
async def submit_human_review(
    thread_id: str,
    review_request: HumanReviewRequest,
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Submit human review feedback and resume workflow
    
    Args:
        thread_id: Thread identifier (full thread ID with timestamp)
        review_request: Human review feedback
        workflow: Workflow instance
    
    Returns:
        Review submission result
    """
    try:
        
        # Get document ID from state
        state = await workflow.get_workflow_state(thread_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        
        document_id = state["document"]["id"]
        
        # Create human feedback object
        human_feedback = {
            "review_id": f"review_{document_id}_{int(datetime.now().timestamp())}",
            "reviewer": review_request.reviewer,
            "decision": review_request.decision,
            "feedback": review_request.feedback,
            "modifications": review_request.modifications,
            "timestamp": datetime.now()
        }
        
        # Resume workflow with feedback
        result = await workflow.resume_workflow(thread_id, human_feedback)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to submit review"))
        
        # Notify via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "human_review_submitted",
                "document_id": document_id,
                "decision": review_request.decision,
                "status": result.get("status", "unknown")
            }
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "message": "Human review submitted successfully",
            "decision": review_request.decision,
            "workflow_status": result.get("status", "unknown")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit human review for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit human review: {str(e)}")


@app.get("/human-review/{thread_id}/context")
async def get_human_review_context(
    thread_id: str,
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Get context information for human review
    
    Args:
        thread_id: Thread identifier (full thread ID with timestamp)
        workflow: Workflow instance
    
    Returns:
        Review context information
    """
    try:
        state = await workflow.get_workflow_state(thread_id)
        
        if not state:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        
        document_id = state["document"]["id"]
        
        # Get human review requests
        review_requests = state.get("human_review_requests", [])
        if not review_requests:
            raise HTTPException(status_code=400, detail="No human review requested for this document")
        
        latest_request = review_requests[-1]
        
        return {
            "document_id": document_id,
            "review_request": latest_request,
            "document_info": {
                "type": state.get("document_type", "unknown"),
                "file_type": state["document"]["file_type"],
                "content_preview": state["document"]["content"][:500] + "..." if len(state["document"]["content"]) > 500 else state["document"]["content"]
            },
            "extracted_data": state.get("extracted_data", {}),
            "validation_issues": state.get("validation_result", {}).get("result", {}),
            "anomalies": state.get("anomalies_detected", []),
            "business_rules": state.get("business_rules_applied", [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get review context for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get review context: {str(e)}")


# WebSocket endpoint for real-time updates
@app.websocket("/workflow/{document_id}/stream")
async def workflow_websocket(websocket: WebSocket, document_id: str):
    """
    WebSocket endpoint for real-time workflow updates
    
    Args:
        websocket: WebSocket connection
        document_id: Document identifier
    """
    await websocket_manager.connect(websocket, document_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            elif message.get("type") == "get_status":
                # Send current status
                workflow = get_workflow_instance()
                thread_id = f"thread_{document_id}"
                status_info = workflow.get_workflow_status(thread_id)
                await websocket.send_json({
                    "type": "status_update",
                    "document_id": document_id,
                    "status": status_info
                })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, document_id)
    except Exception as e:
        logger.error(f"WebSocket error for document {document_id}: {e}")
        websocket_manager.disconnect(websocket, document_id)


# Background processing functions
@traceable(name="process_document_background")
async def process_document_background(
    document_id: str,
    file_path: str,
    file_type: str,
    original_filename: str,
    workflow: DocumentProcessingWorkflow
):
    """Background task for document processing"""
    try:
        logger.info(f"Starting background processing for document: {document_id}")
        
        # Notify start via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "processing_started",
                "document_id": document_id,
                "filename": original_filename,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Process document
        result = await workflow.process_document(
            document_id=document_id,
            content="",  # Will be loaded from file_path
            file_type=file_type,
            metadata={"original_filename": original_filename},
            file_path=file_path
        )
        
        # Notify completion via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "processing_completed" if result["success"] else "processing_failed",
                "document_id": document_id,
                "status": result.get("status", "unknown"),
                "requires_human_review": result.get("requires_human_review", False),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Background processing completed for document: {document_id}")
    
    except Exception as e:
        logger.error(f"Background processing failed for document {document_id}: {e}")
        
        # Notify error via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "processing_error",
                "document_id": document_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@traceable(name="process_text_background")
async def process_text_background(
    document_id: str,
    content: str,
    file_type: str,
    workflow: DocumentProcessingWorkflow
):
    """Background task for text processing"""
    try:
        logger.info(f"Starting background text processing for document: {document_id}")
        
        # Notify start via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "processing_started",
                "document_id": document_id,
                "content_length": len(content),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Process text
        result = await workflow.process_document(
            document_id=document_id,
            content=content,
            file_type=file_type,
            metadata={"source": "direct_text"}
        )
        
        # Notify completion via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "processing_completed" if result["success"] else "processing_failed",
                "document_id": document_id,
                "status": result.get("status", "unknown"),
                "requires_human_review": result.get("requires_human_review", False),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Background text processing completed for document: {document_id}")
    
    except Exception as e:
        logger.error(f"Background text processing failed for document {document_id}: {e}")
        
        # Notify error via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "processing_error",
                "document_id": document_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Simplified endpoints for Lovable frontend
@app.get("/simple-status/{document_id}", response_model=SimpleStatusResponse)
async def get_simple_status(
    document_id: str,
    thread_id: str = Query(..., description="The full thread ID of the workflow"),
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Simplified status endpoint for Lovable frontend
    """
    try:
        status_info = await workflow.get_workflow_status(thread_id)
        
        if "error" in status_info:
            return SimpleStatusResponse(
                document_id=document_id,
                status="error",
                progress_percentage=0.0,
                current_step="error",
                is_complete=False,
                requires_human_review=False,
                error=status_info["error"]
            )
        
        # Calculate progress percentage based on completed agents
        completed_agents = len([agent for agent in status_info.get("agent_status", {}).values() 
                              if agent.get("status") == "completed"])
        total_agents = 9  # We have 9 agents
        progress_percentage = (completed_agents / total_agents) * 100
        
        return SimpleStatusResponse(
            document_id=document_id,
            status=status_info.get("overall_status", "unknown"),
            progress_percentage=progress_percentage,
            current_step=status_info.get("current_agent", "unknown"),
            is_complete=status_info.get("overall_status") == "completed",
            requires_human_review=status_info.get("human_review_required", False)
        )
        
    except Exception as e:
        logger.error(f"Failed to get simple status for {document_id}: {e}")
        return SimpleStatusResponse(
            document_id=document_id,
            status="error",
            progress_percentage=0.0,
            current_step="error",
            is_complete=False,
            requires_human_review=False,
            error=str(e)
        )

@app.post("/upload-and-process")
async def upload_and_process(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Combined upload and process endpoint for Lovable
    """
    try:
        # Generate document ID
        document_id = str(uuid.uuid4())
        timestamp = int(time.time())
        thread_id = f"thread_{document_id}_{timestamp}"
        
        # Save uploaded file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{document_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Start background processing
        background_tasks.add_task(
            process_document_background,
            document_id,
            thread_id,
            file_path,
            file.filename,
            workflow
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "thread_id": thread_id,
            "filename": file.filename,
            "status": "processing",
            "message": "Document uploaded and processing started"
        }
        
    except Exception as e:
        logger.error(f"Failed to upload and process file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================================================
# STANDARD LANGGRAPH CLOUD ENDPOINTS (Client-Ready)
# ============================================================================

class LangGraphInvokeRequest(BaseModel):
    """Standard LangGraph invoke request format"""
    input: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    stream_mode: Optional[str] = "values"

class LangGraphInvokeResponse(BaseModel):
    """Standard LangGraph invoke response format"""
    run_id: str
    status: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]

class LangGraphRunStatus(BaseModel):
    """Standard LangGraph run status format"""
    run_id: str
    status: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str

@app.post("/invoke", response_model=LangGraphInvokeResponse)
async def invoke_workflow(
    request: LangGraphInvokeRequest,
    background_tasks: BackgroundTasks,
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Standard LangGraph Cloud /invoke endpoint
    Starts a document processing workflow
    """
    try:
        # Generate run ID (using document_id format for compatibility)
        document_id = str(uuid.uuid4())
        timestamp = int(time.time())
        run_id = f"run_{document_id}_{timestamp}"
        thread_id = f"thread_{document_id}_{timestamp}"
        
        # Extract input data
        input_data = request.input
        text_content = input_data.get("text_content", "")
        file_type = input_data.get("file_type", "text")
        
        if not text_content:
            raise HTTPException(status_code=400, detail="text_content is required in input")
        
        # Store run metadata for status tracking
        run_metadata = {
            "run_id": run_id,
            "thread_id": thread_id,
            "document_id": document_id,
            "status": "running",
            "input": input_data,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Start background processing
        background_tasks.add_task(
            process_langgraph_workflow,
            run_id,
            thread_id,
            document_id,
            text_content,
            file_type,
            workflow,
            run_metadata
        )
        
        return LangGraphInvokeResponse(
            run_id=run_id,
            status="running",
            input=input_data,
            metadata={
                "document_id": document_id,
                "thread_id": thread_id,
                "created_at": run_metadata["created_at"]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to invoke workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to invoke workflow: {str(e)}")

@app.get("/runs/{run_id}", response_model=LangGraphRunStatus)
async def get_run_status(
    run_id: str,
    workflow: DocumentProcessingWorkflow = Depends(get_workflow_instance)
):
    """
    Standard LangGraph Cloud /runs/{run_id} endpoint
    Gets the status of a running workflow
    """
    try:
        # Extract thread_id from run_id
        if not run_id.startswith("run_"):
            raise HTTPException(status_code=400, detail="Invalid run_id format")
        
        # Parse run_id to get thread_id
        parts = run_id.split("_")
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid run_id format")
        
        document_id = parts[1]
        timestamp = parts[2]
        thread_id = f"thread_{document_id}_{timestamp}"
        
        # Get workflow status
        status_info = workflow.get_workflow_status(thread_id)
        
        if "error" in status_info:
            return LangGraphRunStatus(
                run_id=run_id,
                status="error",
                input={},
                output={"error": status_info["error"]},
                metadata={"document_id": document_id, "thread_id": thread_id},
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
        
        # Map to standard LangGraph format
        overall_status = status_info.get("overall_status", "running")
        langgraph_status = "success" if overall_status == "completed" else overall_status
        
        # Get results if completed
        output_data = None
        if overall_status == "completed":
            try:
                results = workflow.get_workflow_state(thread_id)
                if results:
                    output_data = {
                        "extracted_data": results.get("extracted_data", {}),
                        "validated_data": results.get("validated_data", {}),
                        "confidence_scores": results.get("confidence_scores", {}),
                        "business_rules_applied": results.get("business_rules_applied", []),
                        "anomalies_detected": results.get("anomalies_detected", []),
                        "human_review_required": results.get("human_review_required", False)
                    }
            except Exception as e:
                logger.warning(f"Could not get results for {run_id}: {e}")
        
        return LangGraphRunStatus(
            run_id=run_id,
            status=langgraph_status,
            input={"document_id": document_id},
            output=output_data,
            metadata={
                "document_id": document_id,
                "thread_id": thread_id,
                "progress_percentage": status_info.get("progress_percentage", 0),
                "current_step": status_info.get("current_agent", "unknown"),
                "agent_status": status_info.get("agent_status", {}),
                "human_review_required": status_info.get("human_review_required", False)
            },
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run status for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get run status: {str(e)}")

@app.get("/stream/{run_id}")
async def stream_workflow(run_id: str):
    """
    Standard LangGraph Cloud /stream/{run_id} endpoint
    Streams workflow updates (redirects to WebSocket)
    """
    try:
        # Extract document_id from run_id
        if not run_id.startswith("run_"):
            raise HTTPException(status_code=400, detail="Invalid run_id format")
        
        parts = run_id.split("_")
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid run_id format")
        
        document_id = parts[1]
        
        # Return WebSocket connection info
        return {
            "message": "Use WebSocket for streaming",
            "websocket_url": f"ws://localhost:8000/workflow/{document_id}/stream",
            "run_id": run_id,
            "document_id": document_id
        }
        
    except Exception as e:
        logger.error(f"Failed to setup stream for {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to setup stream: {str(e)}")

# Background processing function for LangGraph standard workflow
@traceable(name="process_langgraph_workflow")
async def process_langgraph_workflow(
    run_id: str,
    thread_id: str,
    document_id: str,
    text_content: str,
    file_type: str,
    workflow: DocumentProcessingWorkflow,
    run_metadata: Dict[str, Any]
):
    """Background task for LangGraph standard workflow processing"""
    try:
        logger.info(f"Starting LangGraph workflow processing for run: {run_id}")
        
        # Notify start via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "workflow_started",
                "run_id": run_id,
                "document_id": document_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Process using existing workflow
        result = await workflow.process_document(
            document_id=document_id,
            content=text_content,
            file_type=file_type,
            metadata={"source": "langgraph_invoke", "run_id": run_id}
        )
        
        # Notify completion via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "workflow_completed",
                "run_id": run_id,
                "document_id": document_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        logger.info(f"LangGraph workflow processing completed for run: {run_id}")
    
    except Exception as e:
        logger.error(f"LangGraph workflow processing failed for run {run_id}: {e}")
        
        # Notify error via WebSocket
        await websocket_manager.broadcast_to_document(
            document_id,
            {
                "type": "workflow_error",
                "run_id": run_id,
                "document_id": document_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )