"""
Coordinator Agent - Controls workflow routing and decision making.
Determines which agent should run next based on current state.
"""

import logging
from typing import Dict, Any, Optional, Literal
from workflows.state_schema import DocumentProcessingState

logger = logging.getLogger(__name__)

# Define the agent flow sequence
AGENT_SEQUENCE = [
    "ingestion",
    "classification", 
    "extraction",
    "validation",
    "rule_evaluation",
    "anomaly_detection",
    "human_review",
    "audit_learning"
]


def coordinator_decision(state: DocumentProcessingState) -> str:
    """
    Coordinator decision function that determines the next agent to run
    
    This function implements the routing logic for the document processing workflow:
    1. Follows sequential flow for normal processing
    2. Routes to human_review when required
    3. Handles error conditions and retries
    4. Manages workflow completion
    
    Args:
        state: Current document processing state
    
    Returns:
        String indicating the next agent to run, or "__end__" to finish workflow
    """
    try:
        current_agent = state.get("current_agent", "")
        status = state.get("status", "pending")
        requires_human_review = state.get("requires_human_review", False)
        human_feedback = state.get("human_feedback")
        
        logger.info(f"Coordinator decision: current_agent={current_agent}, status={status}, "
                   f"requires_human_review={requires_human_review}")
        
        # Handle initial state
        if not current_agent or current_agent == "":
            logger.info("Starting workflow with ingestion agent")
            return "ingestion"
        
        # Handle workflow completion
        if status in ["completed", "failed"] and current_agent == "audit_learning":
            logger.info("Workflow completed, ending")
            return "__end__"
        
        # Handle human review flow
        if requires_human_review and not human_feedback:
            # Need human review but no feedback yet
            if current_agent != "human_review":
                logger.info("Human review required, routing to human_review agent")
                return "human_review"
            else:
                # Already in human review, waiting for feedback
                logger.info("Waiting for human feedback, staying in human_review")
                return "__end__"  # Workflow will be resumed when feedback is provided
        
        # Handle human review completion
        if requires_human_review and human_feedback:
            feedback_decision = human_feedback.get("decision", "")
            
            if feedback_decision == "reject":
                logger.info("Human review rejected, ending workflow")
                return "audit_learning"  # Go to final logging
            elif feedback_decision == "escalate":
                logger.info("Human review escalated, ending workflow for now")
                return "__end__"  # Workflow paused for escalation
            elif feedback_decision in ["approve", "modify"]:
                logger.info("Human review approved/modified, continuing workflow")
                # Continue to next agent after human_review
                return _get_next_sequential_agent("human_review")
        
        # Handle error states
        if status == "failed":
            logger.info("Workflow failed, routing to audit_learning for final logging")
            return "audit_learning"
        
        # Handle sequential flow
        if current_agent in AGENT_SEQUENCE:
            # Check if current agent completed successfully
            current_result = state.get(f"{current_agent}_result")
            
            if current_result is None:
                # Agent hasn't run yet, run it
                logger.info(f"Running {current_agent} agent")
                return current_agent
            
            if not current_result.get("success", False):
                # Current agent failed
                logger.warning(f"Agent {current_agent} failed, checking if workflow should continue")
                
                # Some agents can fail without stopping the workflow
                if current_agent in ["validation", "rule_evaluation", "anomaly_detection"]:
                    logger.info(f"Agent {current_agent} failed but workflow continues")
                    next_agent = _get_next_sequential_agent(current_agent)
                    if next_agent:
                        return next_agent
                    else:
                        return "audit_learning"
                else:
                    # Critical agent failed, end workflow
                    logger.error(f"Critical agent {current_agent} failed, ending workflow")
                    return "audit_learning"
            
            # Current agent succeeded, move to next
            next_agent = _get_next_sequential_agent(current_agent)
            if next_agent:
                logger.info(f"Moving from {current_agent} to {next_agent}")
                return next_agent
            else:
                # Reached end of sequence
                logger.info("Reached end of agent sequence, finalizing with audit_learning")
                return "audit_learning"
        
        # Fallback - if we don't know what to do, go to audit_learning
        logger.warning(f"Unknown state in coordinator, defaulting to audit_learning. "
                      f"current_agent={current_agent}, status={status}")
        return "audit_learning"
    
    except Exception as e:
        logger.error(f"Coordinator decision failed: {e}")
        # In case of coordinator error, try to end gracefully
        return "audit_learning"


def _get_next_sequential_agent(current_agent: str) -> Optional[str]:
    """
    Get the next agent in the sequential flow
    
    Args:
        current_agent: Name of current agent
    
    Returns:
        Name of next agent, or None if at end of sequence
    """
    try:
        current_index = AGENT_SEQUENCE.index(current_agent)
        if current_index < len(AGENT_SEQUENCE) - 1:
            return AGENT_SEQUENCE[current_index + 1]
        else:
            return None
    except ValueError:
        # Current agent not in sequence
        logger.warning(f"Agent {current_agent} not found in sequence")
        return None


def should_interrupt_before_agent(state: DocumentProcessingState, agent_name: str) -> bool:
    """
    Determine if workflow should interrupt before running an agent
    
    This is used by LangGraph's interrupt_before functionality to pause
    the workflow for human intervention.
    
    Args:
        state: Current document processing state
        agent_name: Name of agent about to run
    
    Returns:
        True if workflow should interrupt, False otherwise
    """
    try:
        # Interrupt before human_review if human review is required but no feedback exists
        if agent_name == "human_review":
            requires_review = state.get("requires_human_review", False)
            has_feedback = state.get("human_feedback") is not None
            
            if requires_review and not has_feedback:
                logger.info("Interrupting workflow before human_review agent")
                return True
        
        # Don't interrupt for other agents
        return False
    
    except Exception as e:
        logger.error(f"Error in interrupt check: {e}")
        return False


def get_workflow_status(state: DocumentProcessingState) -> Dict[str, Any]:
    """
    Get comprehensive workflow status information
    
    Args:
        state: Current document processing state
    
    Returns:
        Dictionary with workflow status details
    """
    try:
        # Calculate progress
        completed_agents = len([h for h in state.get("agent_history", []) if h["status"] == "completed"])
        total_agents = len(AGENT_SEQUENCE)
        progress_percentage = (completed_agents / total_agents) * 100
        
        # Get current phase
        current_agent = state.get("current_agent", "")
        if current_agent in AGENT_SEQUENCE:
            current_phase = AGENT_SEQUENCE.index(current_agent) + 1
        else:
            current_phase = 0
        
        # Determine next steps
        next_agent = coordinator_decision(state)
        
        # Calculate processing time
        started_at = state.get("started_at")
        completed_at = state.get("completed_at")
        
        if started_at and completed_at:
            total_time = (completed_at - started_at).total_seconds()
        elif started_at:
            from datetime import datetime
            total_time = (datetime.now() - started_at).total_seconds()
        else:
            total_time = 0
        
        status_info = {
            "workflow_id": state.get("workflow_id", ""),
            "document_id": state["document"]["id"],
            "current_status": state.get("status", "unknown"),
            "current_agent": current_agent,
            "next_agent": next_agent if next_agent != "__end__" else None,
            "progress": {
                "completed_agents": completed_agents,
                "total_agents": total_agents,
                "percentage": progress_percentage,
                "current_phase": current_phase
            },
            "timing": {
                "started_at": started_at.isoformat() if started_at else None,
                "completed_at": completed_at.isoformat() if completed_at else None,
                "total_processing_time": total_time,
                "estimated_remaining_time": _estimate_remaining_time(state, current_agent)
            },
            "human_interaction": {
                "requires_human_review": state.get("requires_human_review", False),
                "human_feedback_provided": state.get("human_feedback") is not None,
                "review_requests": len(state.get("human_review_requests", []))
            },
            "quality_metrics": {
                "overall_confidence": _calculate_overall_confidence(state),
                "errors_count": len(state.get("error_log", [])),
                "anomalies_count": len(state.get("anomalies_detected", [])),
                "business_rules_triggered": len(state.get("business_rules_applied", []))
            },
            "is_complete": next_agent == "__end__" or state.get("status") in ["completed", "failed"],
            "can_continue": next_agent not in ["__end__", None]
        }
        
        return status_info
    
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        return {
            "error": str(e),
            "workflow_id": state.get("workflow_id", ""),
            "document_id": state.get("document", {}).get("id", "unknown")
        }


def _estimate_remaining_time(state: DocumentProcessingState, current_agent: str) -> Optional[float]:
    """Estimate remaining processing time based on completed agents"""
    try:
        # Get average processing time per agent from completed agents
        completed_times = []
        for history_entry in state.get("agent_history", []):
            if history_entry["status"] == "completed" and history_entry.get("result"):
                processing_time = history_entry["result"].get("processing_time", 0)
                if processing_time > 0:
                    completed_times.append(processing_time)
        
        if not completed_times:
            return None
        
        avg_time_per_agent = sum(completed_times) / len(completed_times)
        
        # Calculate remaining agents
        if current_agent in AGENT_SEQUENCE:
            current_index = AGENT_SEQUENCE.index(current_agent)
            remaining_agents = len(AGENT_SEQUENCE) - current_index - 1
        else:
            remaining_agents = len(AGENT_SEQUENCE)
        
        return remaining_agents * avg_time_per_agent
    
    except Exception:
        return None


def _calculate_overall_confidence(state: DocumentProcessingState) -> float:
    """Calculate overall confidence score from all agents"""
    try:
        confidences = []
        
        for agent_name in AGENT_SEQUENCE[:-1]:  # Exclude audit_learning
            result = state.get(f"{agent_name}_result")
            if result and result.get("confidence_score") is not None:
                confidences.append(result["confidence_score"])
        
        if confidences:
            return sum(confidences) / len(confidences)
        else:
            return 0.0
    
    except Exception:
        return 0.0


def validate_workflow_state(state: DocumentProcessingState) -> Dict[str, Any]:
    """
    Validate the current workflow state for consistency
    
    Args:
        state: Current document processing state
    
    Returns:
        Validation results with any issues found
    """
    validation_result = {
        "is_valid": True,
        "issues": [],
        "warnings": []
    }
    
    try:
        # Check required fields
        required_fields = ["document", "workflow_id", "started_at", "agent_history"]
        for field in required_fields:
            if field not in state:
                validation_result["issues"].append(f"Missing required field: {field}")
                validation_result["is_valid"] = False
        
        # Check document structure
        if "document" in state:
            doc = state["document"]
            required_doc_fields = ["id", "content", "file_type"]
            for field in required_doc_fields:
                if field not in doc:
                    validation_result["issues"].append(f"Missing document field: {field}")
                    validation_result["is_valid"] = False
        
        # Check agent history consistency
        agent_history = state.get("agent_history", [])
        current_agent = state.get("current_agent", "")
        
        if current_agent and agent_history:
            # Check if current agent has started
            current_agent_entries = [h for h in agent_history if h["agent_name"] == current_agent]
            if not current_agent_entries:
                validation_result["warnings"].append(f"Current agent {current_agent} not found in history")
        
        # Check status consistency
        status = state.get("status", "")
        requires_review = state.get("requires_human_review", False)
        has_feedback = state.get("human_feedback") is not None
        
        if status == "requires_human_review" and not requires_review:
            validation_result["warnings"].append("Status indicates human review required but flag is False")
        
        if requires_review and status not in ["requires_human_review", "human_review_pending", "human_review_completed"]:
            validation_result["warnings"].append("Human review required but status doesn't reflect this")
        
    except Exception as e:
        validation_result["issues"].append(f"Validation error: {str(e)}")
        validation_result["is_valid"] = False
    
    return validation_result