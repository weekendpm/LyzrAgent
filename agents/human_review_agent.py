"""
Human Review Agent - Handles human-in-the-loop review process.
Seventh agent in the document processing pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json

from workflows.state_schema import (
    DocumentProcessingState, AgentResult, HumanReviewRequest, HumanFeedback,
    add_agent_history_entry, update_agent_result
)

logger = logging.getLogger(__name__)


class HumanReviewManager:
    """Manages human review requests and feedback processing"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize human review manager with configuration"""
        self.config = config
        self.auto_approve_threshold = config.get("auto_approve_threshold", 0.95)
        self.require_review_threshold = config.get("require_review_threshold", 0.6)
        self.escalation_threshold = config.get("escalation_threshold", 0.3)
    
    async def create_review_request(self, state: DocumentProcessingState) -> HumanReviewRequest:
        """
        Create a human review request based on current state
        
        Args:
            state: Current document processing state
        
        Returns:
            Human review request
        """
        try:
            # Analyze why review is needed
            review_reasons = self._analyze_review_reasons(state)
            
            # Determine priority based on issues found
            priority = self._determine_priority(state, review_reasons)
            
            # Generate required actions
            required_actions = self._generate_required_actions(state, review_reasons)
            
            # Create context for reviewer
            context = self._create_review_context(state)
            
            # Determine due date based on priority
            due_date = self._calculate_due_date(priority)
            
            review_request = HumanReviewRequest(
                review_id=f"review_{state['document']['id']}_{int(datetime.now().timestamp())}",
                reason="; ".join(review_reasons),
                priority=priority,
                required_actions=required_actions,
                context=context,
                assigned_to=None,  # Would be assigned by workflow management system
                due_date=due_date
            )
            
            return review_request
        
        except Exception as e:
            logger.error(f"Failed to create review request: {e}")
            # Create minimal review request
            return HumanReviewRequest(
                review_id=f"review_{state['document']['id']}_error",
                reason=f"Review request creation failed: {str(e)}",
                priority="medium",
                required_actions=["manual_review"],
                context={"error": str(e)},
                assigned_to=None,
                due_date=datetime.now() + timedelta(days=1)
            )
    
    def _analyze_review_reasons(self, state: DocumentProcessingState) -> List[str]:
        """Analyze state to determine why review is needed"""
        reasons = []
        
        # Check confidence scores
        extraction_result = state.get("extraction_result", {})
        validation_result = state.get("validation_result", {})
        
        if extraction_result.get("confidence_score", 1.0) < self.require_review_threshold:
            reasons.append(f"Low extraction confidence ({extraction_result.get('confidence_score', 0):.2f})")
        
        if not validation_result.get("success", True):
            error_count = len(validation_result.get("result", {}).get("validation_errors", []))
            reasons.append(f"Data validation failed ({error_count} errors)")
        
        # Check business rules
        rule_result = state.get("rule_evaluation_result", {})
        if rule_result.get("success", True):
            actions_required = rule_result.get("result", {}).get("actions_required", [])
            review_actions = [a for a in actions_required if "review" in a.get("action", "").lower()]
            if review_actions:
                reasons.append(f"Business rules require review ({len(review_actions)} rules triggered)")
        
        # Check anomalies
        anomaly_result = state.get("anomaly_detection_result", {})
        if anomaly_result.get("success", True):
            high_severity_count = anomaly_result.get("result", {}).get("high_severity_count", 0)
            critical_count = anomaly_result.get("result", {}).get("critical_severity_count", 0)
            if high_severity_count > 0 or critical_count > 0:
                reasons.append(f"Anomalies detected ({critical_count} critical, {high_severity_count} high severity)")
        
        # Check for processing errors
        error_log = state.get("error_log", [])
        if error_log:
            reasons.append(f"Processing errors occurred ({len(error_log)} errors)")
        
        # Default reason if no specific issues found
        if not reasons:
            reasons.append("Manual review requested")
        
        return reasons
    
    def _determine_priority(self, state: DocumentProcessingState, reasons: List[str]) -> str:
        """Determine review priority based on state and reasons"""
        # Check for critical issues
        anomaly_result = state.get("anomaly_detection_result", {})
        critical_anomalies = anomaly_result.get("result", {}).get("critical_severity_count", 0)
        
        if critical_anomalies > 0:
            return "urgent"
        
        # Check confidence scores
        extraction_confidence = state.get("extraction_result", {}).get("confidence_score", 1.0)
        validation_confidence = state.get("validation_result", {}).get("confidence_score", 1.0)
        
        min_confidence = min(extraction_confidence, validation_confidence)
        
        if min_confidence < self.escalation_threshold:
            return "high"
        elif min_confidence < self.require_review_threshold:
            return "medium"
        
        # Check business rule priorities
        rule_result = state.get("rule_evaluation_result", {})
        if rule_result.get("success", True):
            actions_required = rule_result.get("result", {}).get("actions_required", [])
            high_priority_actions = [a for a in actions_required if a.get("priority", 3) == 1]
            if high_priority_actions:
                return "high"
        
        return "medium"
    
    def _generate_required_actions(self, state: DocumentProcessingState, reasons: List[str]) -> List[str]:
        """Generate list of actions required from reviewer"""
        actions = []
        
        # Always require verification
        actions.append("verify_extracted_data")
        
        # Check validation issues
        validation_result = state.get("validation_result", {})
        if not validation_result.get("success", True):
            actions.append("correct_validation_errors")
        
        # Check business rule actions
        rule_result = state.get("rule_evaluation_result", {})
        if rule_result.get("success", True):
            actions_required = rule_result.get("result", {}).get("actions_required", [])
            for action in actions_required:
                if action.get("action") == "require_approval":
                    actions.append("approve_document")
                elif action.get("action") == "require_executive_approval":
                    actions.append("escalate_for_executive_approval")
        
        # Check anomalies
        anomalies = state.get("anomalies_detected", [])
        if anomalies:
            actions.append("review_anomalies")
        
        # Check extraction confidence
        extraction_confidence = state.get("extraction_result", {}).get("confidence_score", 1.0)
        if extraction_confidence < self.require_review_threshold:
            actions.append("verify_low_confidence_extractions")
        
        return list(set(actions))  # Remove duplicates
    
    def _create_review_context(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Create context information for reviewer"""
        context = {
            "document_info": {
                "id": state["document"]["id"],
                "type": state.get("document_type", "unknown"),
                "file_type": state["document"]["file_type"],
                "content_length": len(state["document"]["content"])
            },
            "processing_summary": {
                "agents_completed": len([h for h in state["agent_history"] if h["status"] == "completed"]),
                "total_processing_time": sum([
                    h.get("result", {}).get("processing_time", 0) 
                    for h in state["agent_history"] 
                    if h.get("result")
                ]),
                "overall_confidence": self._calculate_overall_confidence(state)
            },
            "extracted_data": state.get("extracted_data", {}),
            "validation_issues": self._summarize_validation_issues(state),
            "business_rule_issues": self._summarize_rule_issues(state),
            "anomalies": state.get("anomalies_detected", []),
            "recommendations": self._generate_reviewer_recommendations(state)
        }
        
        return context
    
    def _calculate_due_date(self, priority: str) -> datetime:
        """Calculate due date based on priority"""
        now = datetime.now()
        
        if priority == "urgent":
            return now + timedelta(hours=2)
        elif priority == "high":
            return now + timedelta(hours=8)
        elif priority == "medium":
            return now + timedelta(days=1)
        else:  # low
            return now + timedelta(days=3)
    
    def _calculate_overall_confidence(self, state: DocumentProcessingState) -> float:
        """Calculate overall processing confidence"""
        confidences = []
        
        for agent_name in ["ingestion", "classification", "extraction", "validation", "rule_evaluation", "anomaly_detection"]:
            result = state.get(f"{agent_name}_result")
            if result and result.get("confidence_score") is not None:
                confidences.append(result["confidence_score"])
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _summarize_validation_issues(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Summarize validation issues for reviewer"""
        validation_result = state.get("validation_result", {})
        if not validation_result.get("success", True):
            result_data = validation_result.get("result", {})
            return {
                "has_issues": True,
                "error_count": result_data.get("error_count", 0),
                "warning_count": result_data.get("warning_count", 0),
                "errors": result_data.get("validation_errors", []),
                "warnings": result_data.get("validation_warnings", [])
            }
        
        return {"has_issues": False}
    
    def _summarize_rule_issues(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Summarize business rule issues for reviewer"""
        rule_result = state.get("rule_evaluation_result", {})
        if rule_result.get("success", True):
            result_data = rule_result.get("result", {})
            return {
                "rules_triggered": result_data.get("rules_triggered_count", 0),
                "compliance_status": result_data.get("compliance_status", "unknown"),
                "risk_level": result_data.get("risk_level", "unknown"),
                "actions_required": result_data.get("actions_required", [])
            }
        
        return {"rules_triggered": 0}
    
    def _generate_reviewer_recommendations(self, state: DocumentProcessingState) -> List[str]:
        """Generate recommendations for reviewer"""
        recommendations = []
        
        # Confidence-based recommendations
        extraction_confidence = state.get("extraction_result", {}).get("confidence_score", 1.0)
        if extraction_confidence < 0.7:
            recommendations.append("Pay special attention to extracted data accuracy due to low confidence")
        
        # Validation-based recommendations
        validation_result = state.get("validation_result", {})
        if not validation_result.get("success", True):
            recommendations.append("Review and correct validation errors before approval")
        
        # Anomaly-based recommendations
        anomalies = state.get("anomalies_detected", [])
        high_severity_anomalies = [a for a in anomalies if a["severity"] in ["high", "critical"]]
        if high_severity_anomalies:
            recommendations.append("Investigate high-severity anomalies before proceeding")
        
        # Business rule recommendations
        rule_result = state.get("rule_evaluation_result", {})
        if rule_result.get("success", True):
            result_data = rule_result.get("result", {})
            rule_recommendations = result_data.get("recommendations", [])
            recommendations.extend(rule_recommendations)
        
        return recommendations
    
    async def process_human_feedback(self, state: DocumentProcessingState, 
                                   feedback: HumanFeedback) -> Dict[str, Any]:
        """
        Process human feedback and determine next steps
        
        Args:
            state: Current document processing state
            feedback: Human feedback
        
        Returns:
            Processing result with next steps
        """
        try:
            result = {
                "feedback_processed": True,
                "decision": feedback["decision"],
                "next_action": None,
                "modifications_applied": False,
                "continue_workflow": False
            }
            
            if feedback["decision"] == "approve":
                result["next_action"] = "continue_workflow"
                result["continue_workflow"] = True
                
            elif feedback["decision"] == "reject":
                result["next_action"] = "stop_workflow"
                result["continue_workflow"] = False
                
            elif feedback["decision"] == "modify":
                # Apply modifications if provided
                modifications = feedback.get("modifications", {})
                if modifications:
                    # Update validated data with modifications
                    validated_data = state.get("validated_data", {})
                    validated_data.update(modifications)
                    state["validated_data"] = validated_data
                    result["modifications_applied"] = True
                
                result["next_action"] = "continue_workflow"
                result["continue_workflow"] = True
                
            elif feedback["decision"] == "escalate":
                result["next_action"] = "escalate_review"
                result["continue_workflow"] = False
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to process human feedback: {e}")
            return {
                "feedback_processed": False,
                "error": str(e),
                "next_action": "stop_workflow",
                "continue_workflow": False
            }


async def human_review_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Human Review Agent - Handles human-in-the-loop review process
    
    Responsibilities:
    1. Create human review requests when needed
    2. Provide context and recommendations to reviewers
    3. Process human feedback and modifications
    4. Determine workflow continuation based on feedback
    5. Handle escalations and approvals
    
    Args:
        state: Current document processing state
    
    Returns:
        Updated state with human review results
    """
    start_time = time.time()
    agent_name = "human_review"
    
    # Add start entry to history
    state = add_agent_history_entry(state, agent_name, "started")
    state["current_agent"] = agent_name
    
    try:
        logger.info(f"Starting human review for document: {state['document']['id']}")
        
        # Initialize review manager
        config = state.get("processing_config", {})
        review_manager = HumanReviewManager(config)
        
        # Check if human feedback is already provided
        human_feedback = state.get("human_feedback")
        
        if human_feedback:
            # Process existing feedback
            logger.info("Processing existing human feedback")
            
            feedback_result = await review_manager.process_human_feedback(state, human_feedback)
            
            # Update state based on feedback
            if feedback_result["continue_workflow"]:
                state["status"] = "human_review_completed"
            else:
                state["status"] = "human_review_pending" if feedback_result["next_action"] == "escalate_review" else "failed"
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create result
            result = AgentResult(
                success=feedback_result["feedback_processed"],
                result={
                    "review_completed": True,
                    "decision": feedback_result["decision"],
                    "next_action": feedback_result["next_action"],
                    "modifications_applied": feedback_result.get("modifications_applied", False),
                    "continue_workflow": feedback_result["continue_workflow"],
                    "feedback_details": {
                        "reviewer": human_feedback["reviewer"],
                        "feedback": human_feedback["feedback"],
                        "timestamp": human_feedback["timestamp"]
                    }
                },
                error=feedback_result.get("error"),
                confidence_score=1.0 if feedback_result["feedback_processed"] else 0.0,
                processing_time=processing_time,
                timestamp=datetime.now()
            )
            
        else:
            # Create review request
            logger.info("Creating human review request")
            
            review_request = await review_manager.create_review_request(state)
            
            # Add review request to state
            state["human_review_requests"].append(review_request)
            state["status"] = "requires_human_review"
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create result
            result = AgentResult(
                success=True,
                result={
                    "review_completed": False,
                    "review_request_created": True,
                    "review_id": review_request["review_id"],
                    "priority": review_request["priority"],
                    "due_date": review_request["due_date"].isoformat(),
                    "required_actions": review_request["required_actions"],
                    "reason": review_request["reason"],
                    "awaiting_human_input": True
                },
                error=None,
                confidence_score=0.5,  # Neutral confidence while awaiting review
                processing_time=processing_time,
                timestamp=datetime.now()
            )
        
        # Update state
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "completed", result)
        
        logger.info(f"Human review agent completed: {result['result']}")
        
        return state
    
    except Exception as e:
        # Handle errors
        processing_time = time.time() - start_time
        error_msg = f"Human review processing failed: {str(e)}"
        logger.error(error_msg)
        
        # Create error result
        result = AgentResult(
            success=False,
            result={},
            error=error_msg,
            confidence_score=0.0,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        # Update state with error
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "failed", result, error_msg)
        state["error_log"].append(error_msg)
        
        return state