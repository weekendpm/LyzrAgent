"""
Document Processing Workflow using LangGraph.
Assembles all agents into a coordinated workflow with human-in-the-loop capabilities.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

# Import all agents
from agents.ingestion_agent import ingestion_agent
from agents.classification_agent import classification_agent
from agents.extraction_agent import extraction_agent
from agents.validation_agent import validation_agent
from agents.rule_evaluation_agent import rule_evaluation_agent
from agents.anomaly_detection_agent import anomaly_detection_agent
from agents.human_review_agent import human_review_agent
from agents.audit_learning_agent import audit_learning_agent

# Import coordinator
from agents.coordinator_agent import coordinator_decision, should_interrupt_before_agent, coordinator_agent

# Import state schema
from workflows.state_schema import DocumentProcessingState, WorkflowConfig

logger = logging.getLogger(__name__)


class DocumentProcessingWorkflow:
    """
    Document Processing Workflow Manager
    
    Orchestrates the complete document processing pipeline using LangGraph:
    1. Ingestion - File processing and content extraction
    2. Classification - Document type identification
    3. Extraction - Structured data extraction
    4. Validation - Data quality validation
    5. Rule Evaluation - Business rules application
    6. Anomaly Detection - Unusual pattern detection
    7. Human Review - Human-in-the-loop intervention
    8. Audit Learning - Final logging and learning
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None):
        """
        Initialize workflow with configuration
        
        Args:
            config: Workflow configuration (optional)
        """
        self.config = config or WorkflowConfig()
        self.checkpointer = MemorySaver()
        self.workflow = self._build_workflow()
        logger.info("Document processing workflow initialized")
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow with all agents and routing logic
        
        Returns:
            Compiled StateGraph workflow
        """
        # Create state graph
        workflow = StateGraph(DocumentProcessingState)
        
        # Add coordinator as the first node
        workflow.add_node("coordinator", coordinator_agent)
        
        # Add all agent nodes
        workflow.add_node("ingestion", ingestion_agent)
        workflow.add_node("classification", classification_agent)
        workflow.add_node("extraction", extraction_agent)
        workflow.add_node("validation", validation_agent)
        workflow.add_node("rule_evaluation", rule_evaluation_agent)
        workflow.add_node("anomaly_detection", anomaly_detection_agent)
        workflow.add_node("human_review", human_review_agent)
        workflow.add_node("audit_learning", audit_learning_agent)
        
        # Set entry point to coordinator
        workflow.set_entry_point("coordinator")
        
        # Add routing from coordinator to first agent
        workflow.add_conditional_edges(
            "coordinator",
            coordinator_decision,
            {
                "ingestion": "ingestion",
                "classification": "classification",
                "extraction": "extraction",
                "validation": "validation",
                "rule_evaluation": "rule_evaluation",
                "anomaly_detection": "anomaly_detection",
                "human_review": "human_review",
                "audit_learning": "audit_learning",
                "__end__": END
            }
        )
        
        # Add conditional routing using coordinator
        workflow.add_conditional_edges(
            "ingestion",
            coordinator_decision,
            {
                "classification": "classification",
                "audit_learning": "audit_learning",
                "__end__": END
            }
        )
        
        workflow.add_conditional_edges(
            "classification",
            coordinator_decision,
            {
                "extraction": "extraction",
                "audit_learning": "audit_learning",
                "__end__": END
            }
        )
        
        workflow.add_conditional_edges(
            "extraction",
            coordinator_decision,
            {
                "validation": "validation",
                "audit_learning": "audit_learning",
                "__end__": END
            }
        )
        
        workflow.add_conditional_edges(
            "validation",
            coordinator_decision,
            {
                "rule_evaluation": "rule_evaluation",
                "audit_learning": "audit_learning",
                "__end__": END
            }
        )
        
        workflow.add_conditional_edges(
            "rule_evaluation",
            coordinator_decision,
            {
                "anomaly_detection": "anomaly_detection",
                "human_review": "human_review",
                "audit_learning": "audit_learning",
                "__end__": END
            }
        )
        
        workflow.add_conditional_edges(
            "anomaly_detection",
            coordinator_decision,
            {
                "human_review": "human_review",
                "audit_learning": "audit_learning",
                "__end__": END
            }
        )
        
        workflow.add_conditional_edges(
            "human_review",
            coordinator_decision,
            {
                "audit_learning": "audit_learning",
                "__end__": END
            }
        )
        
        # Audit learning always ends the workflow
        workflow.add_edge("audit_learning", END)
        
        # Compile workflow with checkpointer and interrupts
        compiled_workflow = workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_review"]  # Interrupt before human review for human-in-the-loop
        )
        
        return compiled_workflow
    
    async def process_document(self, document_id: str, content: str, file_type: str, 
                             metadata: Optional[Dict[str, Any]] = None,
                             file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a document through the complete workflow
        
        Args:
            document_id: Unique identifier for the document
            content: Document content (text or file path)
            file_type: Type of file (pdf, docx, txt, etc.)
            metadata: Additional metadata about the document
            file_path: Path to file if processing from file
        
        Returns:
            Processing results
        """
        try:
            logger.info(f"Starting document processing for: {document_id}")
            
            # Create initial state
            from workflows.state_schema import create_initial_state
            initial_state = create_initial_state(
                document_id=document_id,
                content=content,
                file_type=file_type,
                metadata=metadata,
                config=self.config
            )
            
            # Add file path if provided
            if file_path:
                initial_state["document"]["file_path"] = file_path
            
            # Create thread configuration
            thread_config = {
                "configurable": {
                    "thread_id": f"thread_{document_id}_{int(datetime.now().timestamp())}"
                }
            }
            
            # Run workflow
            result = await self._run_workflow(initial_state, thread_config)
            
            return {
                "success": True,
                "document_id": document_id,
                "workflow_id": initial_state["workflow_id"],
                "thread_id": thread_config["configurable"]["thread_id"],
                "final_state": result,
                "status": result.get("status", "unknown"),
                "requires_human_review": result.get("requires_human_review", False)
            }
        
        except Exception as e:
            logger.error(f"Document processing failed for {document_id}: {e}")
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e),
                "status": "failed"
            }
    
    async def _run_workflow(self, initial_state: DocumentProcessingState, 
                          thread_config: Dict[str, Any]) -> DocumentProcessingState:
        """
        Run the workflow with proper error handling and state management
        
        Args:
            initial_state: Initial document processing state
            thread_config: Thread configuration for checkpointing
        
        Returns:
            Final document processing state
        """
        try:
            # Stream workflow execution
            final_state = None
            
            async for event in self.workflow.astream(initial_state, thread_config):
                logger.debug(f"Workflow event: {event}")
                
                # Update final state with each event
                for node_name, node_state in event.items():
                    if isinstance(node_state, dict):
                        final_state = node_state
            
            if final_state is None:
                raise ValueError("Workflow did not produce any output")
            
            return final_state
        
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            # Return state with error information
            error_state = initial_state.copy()
            error_state["status"] = "failed"
            error_state["error_log"].append(f"Workflow execution failed: {str(e)}")
            error_state["completed_at"] = datetime.now()
            return error_state
    
    async def resume_workflow(self, thread_id: str, human_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resume workflow after human review with feedback
        
        Args:
            thread_id: Thread ID of the paused workflow
            human_feedback: Human feedback to apply
        
        Returns:
            Resumed workflow results
        """
        try:
            logger.info(f"Resuming workflow {thread_id} with human feedback")
            
            # Get current state
            thread_config = {"configurable": {"thread_id": thread_id}}
            current_state = await self.get_workflow_state(thread_id)
            
            if not current_state:
                raise ValueError(f"No workflow state found for thread {thread_id}")
            
            # Apply human feedback
            from workflows.state_schema import HumanFeedback
            feedback_obj = HumanFeedback(**human_feedback)
            current_state["human_feedback"] = feedback_obj
            
            # Update status
            if feedback_obj["decision"] in ["approve", "modify"]:
                current_state["status"] = "human_review_completed"
            elif feedback_obj["decision"] == "reject":
                current_state["status"] = "failed"
            
            # Resume workflow
            final_state = None
            async for event in self.workflow.astream(None, thread_config):
                logger.debug(f"Resume workflow event: {event}")
                
                for node_name, node_state in event.items():
                    if isinstance(node_state, dict):
                        final_state = node_state
            
            return {
                "success": True,
                "thread_id": thread_id,
                "final_state": final_state,
                "status": final_state.get("status", "unknown") if final_state else "unknown"
            }
        
        except Exception as e:
            logger.error(f"Failed to resume workflow {thread_id}: {e}")
            return {
                "success": False,
                "thread_id": thread_id,
                "error": str(e)
            }
    
    async def get_workflow_state(self, thread_id: str) -> Optional[DocumentProcessingState]:
        """
        Get current state of a workflow
        
        Args:
            thread_id: Thread ID of the workflow
        
        Returns:
            Current workflow state or None if not found
        """
        try:
            thread_config = {"configurable": {"thread_id": thread_id}}
            state_snapshot = self.workflow.get_state(thread_config)
            
            if state_snapshot and state_snapshot.values:
                return state_snapshot.values
            else:
                return None
        
        except Exception as e:
            logger.error(f"Failed to get workflow state for {thread_id}: {e}")
            return None
    
    async def get_workflow_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get workflow execution history
        
        Args:
            thread_id: Thread ID of the workflow
        
        Returns:
            List of workflow state snapshots
        """
        try:
            thread_config = {"configurable": {"thread_id": thread_id}}
            history = []
            
            # Get state history from checkpointer
            for state_snapshot in self.workflow.get_state_history(thread_config):
                history.append({
                    "timestamp": state_snapshot.created_at,
                    "step": state_snapshot.step,
                    "state": state_snapshot.values,
                    "next_steps": state_snapshot.next
                })
            
            return history
        
        except Exception as e:
            logger.error(f"Failed to get workflow history for {thread_id}: {e}")
            return []
    
    def get_workflow_status(self, thread_id: str) -> Dict[str, Any]:
        """
        Get comprehensive workflow status
        
        Args:
            thread_id: Thread ID of the workflow
        
        Returns:
            Workflow status information
        """
        try:
            import asyncio
            state = asyncio.run(self.get_workflow_state(thread_id))
            if state:
                from agents.coordinator_agent import get_workflow_status
                return get_workflow_status(state)
            else:
                return {
                    "error": "Workflow not found",
                    "thread_id": thread_id
                }
        
        except Exception as e:
            logger.error(f"Failed to get workflow status for {thread_id}: {e}")
            return {
                "error": str(e),
                "thread_id": thread_id
            }


# Global workflow instance
_workflow_instance = None


def get_workflow(config: Optional[WorkflowConfig] = None) -> DocumentProcessingWorkflow:
    """
    Get or create global workflow instance
    
    Args:
        config: Workflow configuration (optional)
    
    Returns:
        DocumentProcessingWorkflow instance
    """
    global _workflow_instance
    
    if _workflow_instance is None:
        _workflow_instance = DocumentProcessingWorkflow(config)
    
    return _workflow_instance


async def process_document_simple(document_id: str, content: str, file_type: str, 
                                file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple interface for document processing
    
    Args:
        document_id: Unique identifier for the document
        content: Document content
        file_type: Type of file
        file_path: Path to file if processing from file
    
    Returns:
        Processing results
    """
    workflow = get_workflow()
    return await workflow.process_document(
        document_id=document_id,
        content=content,
        file_type=file_type,
        file_path=file_path
    )


# Export main components
__all__ = [
    "DocumentProcessingWorkflow",
    "get_workflow", 
    "process_document_simple"
]