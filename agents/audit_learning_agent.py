"""
Audit Learning Agent - Final agent that logs processing results and learns from outcomes.
Ninth and final agent in the document processing pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import os

from workflows.state_schema import (
    DocumentProcessingState, AgentResult, 
    add_agent_history_entry, update_agent_result
)

logger = logging.getLogger(__name__)


class AuditLogger:
    """Handles audit logging and metrics collection"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize audit logger with configuration"""
        self.config = config
        self.log_directory = config.get("audit_log_directory", "audit_logs")
        self.enable_learning = config.get("enable_learning", True)
        self._ensure_log_directory()
    
    def _ensure_log_directory(self):
        """Ensure audit log directory exists"""
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
    
    async def log_processing_session(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """
        Log complete processing session for audit and learning
        
        Args:
            state: Final document processing state
        
        Returns:
            Audit logging results
        """
        try:
            # Create comprehensive audit record
            audit_record = self._create_audit_record(state)
            
            # Save audit record
            await self._save_audit_record(audit_record)
            
            # Collect metrics
            metrics = self._collect_metrics(state)
            
            # Update learning data if enabled
            learning_insights = {}
            if self.enable_learning:
                learning_insights = await self._update_learning_data(state, audit_record)
            
            return {
                "audit_logged": True,
                "audit_id": audit_record["audit_id"],
                "metrics": metrics,
                "learning_insights": learning_insights,
                "log_file": audit_record.get("log_file")
            }
        
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")
            return {
                "audit_logged": False,
                "error": str(e),
                "metrics": {},
                "learning_insights": {}
            }
    
    def _create_audit_record(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Create comprehensive audit record"""
        audit_id = f"audit_{state['document']['id']}_{int(datetime.now().timestamp())}"
        
        # Calculate total processing time
        total_processing_time = 0
        if state.get("completed_at") and state.get("started_at"):
            total_processing_time = (state["completed_at"] - state["started_at"]).total_seconds()
        
        audit_record = {
            "audit_id": audit_id,
            "timestamp": datetime.now().isoformat(),
            "document_info": {
                "document_id": state["document"]["id"],
                "document_type": state.get("document_type"),
                "file_type": state["document"]["file_type"],
                "file_size": state["document"].get("file_size"),
                "content_length": len(state["document"]["content"])
            },
            "workflow_info": {
                "workflow_id": state["workflow_id"],
                "status": state["status"],
                "total_processing_time": total_processing_time,
                "started_at": state["started_at"].isoformat(),
                "completed_at": state.get("completed_at").isoformat() if state.get("completed_at") else None
            },
            "agent_performance": self._analyze_agent_performance(state),
            "data_quality": self._analyze_data_quality(state),
            "business_impact": self._analyze_business_impact(state),
            "human_interaction": self._analyze_human_interaction(state),
            "errors_and_issues": self._collect_errors_and_issues(state),
            "final_results": {
                "extracted_data": state.get("extracted_data", {}),
                "validated_data": state.get("validated_data", {}),
                "business_rules_applied": len(state.get("business_rules_applied", [])),
                "anomalies_detected": len(state.get("anomalies_detected", [])),
                "human_review_required": state.get("requires_human_review", False)
            }
        }
        
        return audit_record
    
    def _analyze_agent_performance(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Analyze performance of each agent"""
        performance = {}
        
        agent_names = ["ingestion", "classification", "extraction", "validation", 
                      "rule_evaluation", "anomaly_detection", "human_review", "audit_learning"]
        
        for agent_name in agent_names:
            result = state.get(f"{agent_name}_result")
            if result:
                performance[agent_name] = {
                    "success": result.get("success", False),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "processing_time": result.get("processing_time", 0.0),
                    "error": result.get("error")
                }
        
        # Calculate overall performance metrics
        successful_agents = sum(1 for p in performance.values() if p["success"])
        total_agents = len(performance)
        avg_confidence = sum(p["confidence_score"] for p in performance.values()) / max(total_agents, 1)
        total_processing_time = sum(p["processing_time"] for p in performance.values())
        
        performance["overall"] = {
            "success_rate": successful_agents / max(total_agents, 1),
            "average_confidence": avg_confidence,
            "total_processing_time": total_processing_time,
            "agents_completed": successful_agents,
            "agents_total": total_agents
        }
        
        return performance
    
    def _analyze_data_quality(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Analyze data quality metrics"""
        quality_metrics = {
            "extraction_quality": {},
            "validation_quality": {},
            "overall_quality": {}
        }
        
        # Extraction quality
        extraction_result = state.get("extraction_result", {})
        if extraction_result.get("success"):
            result_data = extraction_result.get("result", {})
            quality_metrics["extraction_quality"] = {
                "fields_extracted": result_data.get("field_count", 0),
                "non_null_fields": result_data.get("non_null_fields", 0),
                "extraction_confidence": extraction_result.get("confidence_score", 0.0),
                "extraction_method": result_data.get("extraction_method", "unknown")
            }
        
        # Validation quality
        validation_result = state.get("validation_result", {})
        if validation_result:
            result_data = validation_result.get("result", {})
            quality_metrics["validation_quality"] = {
                "is_valid": result_data.get("is_valid", False),
                "error_count": result_data.get("error_count", 0),
                "warning_count": result_data.get("warning_count", 0),
                "corrected_fields": result_data.get("corrected_fields", 0),
                "validation_confidence": validation_result.get("confidence_score", 0.0)
            }
        
        # Overall quality score
        extraction_conf = extraction_result.get("confidence_score", 0.0)
        validation_conf = validation_result.get("confidence_score", 0.0)
        
        quality_metrics["overall_quality"] = {
            "combined_confidence": (extraction_conf + validation_conf) / 2,
            "data_completeness": self._calculate_data_completeness(state),
            "processing_success": state["status"] in ["completed", "human_review_completed"]
        }
        
        return quality_metrics
    
    def _analyze_business_impact(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Analyze business impact and compliance"""
        impact = {
            "compliance_status": "unknown",
            "risk_level": "unknown",
            "business_rules_triggered": 0,
            "anomalies_impact": "low",
            "processing_efficiency": {}
        }
        
        # Business rules impact
        rule_result = state.get("rule_evaluation_result", {})
        if rule_result.get("success"):
            result_data = rule_result.get("result", {})
            impact["compliance_status"] = result_data.get("compliance_status", "unknown")
            impact["risk_level"] = result_data.get("risk_level", "unknown")
            impact["business_rules_triggered"] = result_data.get("rules_triggered_count", 0)
        
        # Anomalies impact
        anomaly_result = state.get("anomaly_detection_result", {})
        if anomaly_result.get("success"):
            result_data = anomaly_result.get("result", {})
            critical_count = result_data.get("critical_severity_count", 0)
            high_count = result_data.get("high_severity_count", 0)
            
            if critical_count > 0:
                impact["anomalies_impact"] = "critical"
            elif high_count > 0:
                impact["anomalies_impact"] = "high"
            elif result_data.get("anomalies_detected_count", 0) > 0:
                impact["anomalies_impact"] = "medium"
        
        # Processing efficiency
        total_time = 0
        if state.get("completed_at") and state.get("started_at"):
            total_time = (state["completed_at"] - state["started_at"]).total_seconds()
        
        impact["processing_efficiency"] = {
            "total_processing_time": total_time,
            "human_review_required": state.get("requires_human_review", False),
            "automation_rate": 1.0 if not state.get("requires_human_review", False) else 0.5,
            "error_count": len(state.get("error_log", []))
        }
        
        return impact
    
    def _analyze_human_interaction(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Analyze human interaction patterns"""
        interaction = {
            "review_required": state.get("requires_human_review", False),
            "review_requests": len(state.get("human_review_requests", [])),
            "feedback_provided": state.get("human_feedback") is not None,
            "review_outcome": None,
            "review_time": None
        }
        
        if state.get("human_feedback"):
            feedback = state["human_feedback"]
            interaction["review_outcome"] = feedback["decision"]
            interaction["reviewer"] = feedback["reviewer"]
            
            # Calculate review time if available
            review_requests = state.get("human_review_requests", [])
            if review_requests:
                request_time = review_requests[-1].get("due_date")  # This would be request creation time in real implementation
                feedback_time = feedback["timestamp"]
                if isinstance(feedback_time, str):
                    feedback_time = datetime.fromisoformat(feedback_time)
                # Review time calculation would need proper request timestamp
        
        return interaction
    
    def _collect_errors_and_issues(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Collect all errors and issues encountered"""
        issues = {
            "processing_errors": state.get("error_log", []),
            "validation_errors": [],
            "business_rule_violations": [],
            "anomalies": state.get("anomalies_detected", []),
            "agent_failures": []
        }
        
        # Collect validation errors
        validation_result = state.get("validation_result", {})
        if validation_result.get("result"):
            issues["validation_errors"] = validation_result["result"].get("validation_errors", [])
        
        # Collect business rule violations
        rule_result = state.get("rule_evaluation_result", {})
        if rule_result.get("result"):
            actions_required = rule_result["result"].get("actions_required", [])
            issues["business_rule_violations"] = [
                action for action in actions_required 
                if action.get("priority", 3) <= 2  # High priority violations
            ]
        
        # Collect agent failures
        for agent_name in ["ingestion", "classification", "extraction", "validation", 
                          "rule_evaluation", "anomaly_detection", "human_review"]:
            result = state.get(f"{agent_name}_result")
            if result and not result.get("success", True):
                issues["agent_failures"].append({
                    "agent": agent_name,
                    "error": result.get("error"),
                    "timestamp": result.get("timestamp")
                })
        
        return issues
    
    def _calculate_data_completeness(self, state: DocumentProcessingState) -> float:
        """Calculate data completeness score"""
        extracted_data = state.get("extracted_data", {})
        if not extracted_data:
            return 0.0
        
        total_fields = len(extracted_data)
        non_null_fields = len([v for v in extracted_data.values() if v is not None and v != ""])
        
        return non_null_fields / max(total_fields, 1)
    
    async def _save_audit_record(self, audit_record: Dict[str, Any]):
        """Save audit record to file"""
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_{audit_record['audit_id']}_{timestamp}.json"
            filepath = os.path.join(self.log_directory, filename)
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(audit_record, f, indent=2, default=str)
            
            audit_record["log_file"] = filepath
            logger.info(f"Audit record saved to {filepath}")
        
        except Exception as e:
            logger.error(f"Failed to save audit record: {e}")
    
    def _collect_metrics(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Collect key performance metrics"""
        metrics = {
            "processing_time": 0,
            "success_rate": 0,
            "automation_rate": 0,
            "data_quality_score": 0,
            "confidence_score": 0,
            "error_rate": 0
        }
        
        try:
            # Processing time
            if state.get("completed_at") and state.get("started_at"):
                metrics["processing_time"] = (state["completed_at"] - state["started_at"]).total_seconds()
            
            # Success rate (based on agent completion)
            completed_agents = len([h for h in state["agent_history"] if h["status"] == "completed"])
            total_agents = len(state["agent_history"])
            metrics["success_rate"] = completed_agents / max(total_agents, 1)
            
            # Automation rate
            metrics["automation_rate"] = 0.5 if state.get("requires_human_review", False) else 1.0
            
            # Data quality score
            metrics["data_quality_score"] = self._calculate_data_completeness(state)
            
            # Average confidence score
            confidences = []
            for agent_name in ["ingestion", "classification", "extraction", "validation"]:
                result = state.get(f"{agent_name}_result")
                if result and result.get("confidence_score") is not None:
                    confidences.append(result["confidence_score"])
            
            metrics["confidence_score"] = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Error rate
            total_errors = len(state.get("error_log", []))
            metrics["error_rate"] = total_errors / max(total_agents, 1)
        
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
        
        return metrics
    
    async def _update_learning_data(self, state: DocumentProcessingState, 
                                  audit_record: Dict[str, Any]) -> Dict[str, Any]:
        """Update learning data for future improvements"""
        learning_insights = {
            "patterns_identified": [],
            "improvement_opportunities": [],
            "confidence_calibration": {},
            "performance_trends": {}
        }
        
        try:
            # Identify patterns in processing
            learning_insights["patterns_identified"] = self._identify_patterns(state, audit_record)
            
            # Identify improvement opportunities
            learning_insights["improvement_opportunities"] = self._identify_improvements(state, audit_record)
            
            # Confidence calibration insights
            learning_insights["confidence_calibration"] = self._analyze_confidence_calibration(state)
            
            # Performance trends (would require historical data in real implementation)
            learning_insights["performance_trends"] = {"note": "Requires historical data for trend analysis"}
        
        except Exception as e:
            logger.error(f"Learning data update failed: {e}")
            learning_insights["error"] = str(e)
        
        return learning_insights
    
    def _identify_patterns(self, state: DocumentProcessingState, audit_record: Dict[str, Any]) -> List[str]:
        """Identify patterns in processing results"""
        patterns = []
        
        # Document type patterns
        doc_type = state.get("document_type", "unknown")
        if doc_type != "unknown":
            patterns.append(f"Document type: {doc_type}")
        
        # Processing patterns
        if state.get("requires_human_review", False):
            patterns.append("Required human review")
        
        # Error patterns
        if state.get("error_log"):
            patterns.append("Processing errors encountered")
        
        # Confidence patterns
        avg_confidence = audit_record.get("agent_performance", {}).get("overall", {}).get("average_confidence", 0)
        if avg_confidence < 0.7:
            patterns.append("Low confidence processing")
        elif avg_confidence > 0.9:
            patterns.append("High confidence processing")
        
        return patterns
    
    def _identify_improvements(self, state: DocumentProcessingState, audit_record: Dict[str, Any]) -> List[str]:
        """Identify opportunities for improvement"""
        improvements = []
        
        # Performance improvements
        total_time = audit_record.get("workflow_info", {}).get("total_processing_time", 0)
        if total_time > 300:  # 5 minutes
            improvements.append("Consider optimizing processing time")
        
        # Confidence improvements
        extraction_result = state.get("extraction_result", {})
        if extraction_result.get("confidence_score", 1.0) < 0.8:
            improvements.append("Improve extraction accuracy")
        
        # Validation improvements
        validation_result = state.get("validation_result", {})
        if validation_result.get("result", {}).get("error_count", 0) > 0:
            improvements.append("Enhance data validation rules")
        
        # Anomaly detection improvements
        anomaly_result = state.get("anomaly_detection_result", {})
        if anomaly_result.get("result", {}).get("anomalies_detected_count", 0) > 3:
            improvements.append("Review anomaly detection thresholds")
        
        return improvements
    
    def _analyze_confidence_calibration(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """Analyze how well confidence scores match actual performance"""
        calibration = {
            "extraction_calibration": "unknown",
            "validation_calibration": "unknown",
            "overall_calibration": "unknown"
        }
        
        # This would require comparison with ground truth data
        # For now, provide basic analysis
        
        extraction_result = state.get("extraction_result", {})
        validation_result = state.get("validation_result", {})
        
        if extraction_result.get("success") and extraction_result.get("confidence_score", 0) > 0.8:
            calibration["extraction_calibration"] = "well_calibrated"
        elif not extraction_result.get("success") and extraction_result.get("confidence_score", 0) > 0.8:
            calibration["extraction_calibration"] = "overconfident"
        
        return calibration


async def audit_learning_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Audit Learning Agent - Final agent that logs results and learns from outcomes
    
    Responsibilities:
    1. Create comprehensive audit logs
    2. Collect performance metrics
    3. Analyze processing patterns
    4. Identify improvement opportunities
    5. Update learning data for future enhancements
    6. Finalize workflow processing
    
    Args:
        state: Current document processing state
    
    Returns:
        Updated state with audit and learning results
    """
    start_time = time.time()
    agent_name = "audit_learning"
    
    # Add start entry to history
    state = add_agent_history_entry(state, agent_name, "started")
    state["current_agent"] = agent_name
    
    try:
        logger.info(f"Starting audit and learning for document: {state['document']['id']}")
        
        # Set completion time
        state["completed_at"] = datetime.now()
        
        # Initialize audit logger
        config = state.get("processing_config", {})
        audit_logger = AuditLogger(config)
        
        # Perform audit logging and learning
        audit_results = await audit_logger.log_processing_session(state)
        
        # Update final status
        if state["status"] not in ["failed", "human_review_pending"]:
            state["status"] = "completed"
        
        # Calculate total processing time
        total_time = (state["completed_at"] - state["started_at"]).total_seconds()
        state["total_processing_time"] = total_time
        
        # Calculate processing time for this agent
        processing_time = time.time() - start_time
        
        # Create result
        result = AgentResult(
            success=audit_results["audit_logged"],
            result={
                "audit_completed": audit_results["audit_logged"],
                "audit_id": audit_results.get("audit_id"),
                "metrics": audit_results.get("metrics", {}),
                "learning_insights": audit_results.get("learning_insights", {}),
                "log_file": audit_results.get("log_file"),
                "workflow_completed": True,
                "final_status": state["status"],
                "total_workflow_time": total_time
            },
            error=audit_results.get("error"),
            confidence_score=1.0 if audit_results["audit_logged"] else 0.0,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        # Update state
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "completed", result)
        
        logger.info(f"Audit and learning completed: workflow finished with status '{state['status']}' "
                   f"in {total_time:.2f} seconds")
        
        return state
    
    except Exception as e:
        # Handle errors
        processing_time = time.time() - start_time
        error_msg = f"Audit and learning failed: {str(e)}"
        logger.error(error_msg)
        
        # Still try to set completion time and status
        state["completed_at"] = datetime.now()
        if state["status"] not in ["failed", "human_review_pending"]:
            state["status"] = "completed_with_errors"
        
        # Create error result
        result = AgentResult(
            success=False,
            result={
                "audit_completed": False,
                "workflow_completed": True,
                "final_status": state["status"]
            },
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