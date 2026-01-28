"""
FastAPI application for document processing platform.
Provides REST API and WebSocket endpoints for the document processing workflow.
LangGraph Cloud compatible with LangSmith tracing.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
import uvicorn

# LangSmith tracing imports
from langsmith import traceable
from langchain.callbacks import LangChainTracer

# Import workflow components
from workflows.document_workflow import get_workflow, DocumentProcessingWorkflow
from workflows.state_schema import WorkflowConfig, HumanFeedback
from api.websocket_manager import WebSocketManager

# Configure LangSmith tracing
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "document-processor")

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Document Processing Platform",
    description="Advanced document processing with AI agents and human-in-the-loop capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for production and development
def get_cors_origins():
    """Get CORS origins from environment or use defaults"""
    env_origins = os.environ.get("ALLOWED_ORIGINS", "")
    if env_origins:
        return env_origins.split(",")
    
    # Default origins for development and Lovable
    return [
        "http://localhost:3000",  # Local development
        "https://*.lovable.dev",  # Lovable preview URLs
        "https://*.lovableproject.com",  # Lovable production URLs
        "*" if os.environ.get("ENVIRONMENT") != "production" else ""
    ]

# Add CORS middleware - Lovable and LangGraph Cloud ready
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin for origin in get_cors_origins() if origin],
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


# Development and production server
if __name__ == "__main__":
    # Get port from environment (for cloud deployment)
    port = int(os.environ.get("PORT", 8000))
    
    # Determine if we're in development or production
    is_development = os.environ.get("ENVIRONMENT") != "production"
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        reload=is_development,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
        workers=1 if is_development else int(os.environ.get("WORKERS", "1"))
    )