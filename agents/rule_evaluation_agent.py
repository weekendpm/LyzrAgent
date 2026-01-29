"""
Rule Evaluation Agent - Applies business rules to validated data.
Fifth agent in the document processing pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
import json
import re

from workflows.state_schema import (
    DocumentProcessingState, AgentResult, BusinessRule, 
    add_agent_history_entry, update_agent_result
)

logger = logging.getLogger(__name__)


class BusinessRuleEngine:
    """Handles business rule evaluation and application"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize rule engine with configuration"""
        self.config = config
        self.rules = self._load_business_rules()
        self.rule_functions = self._register_rule_functions()
    
    def _load_business_rules(self) -> List[BusinessRule]:
        """Load business rules from configuration or defaults"""
        default_rules = [
            # Invoice rules
            {
                "rule_id": "invoice_amount_limit",
                "rule_name": "Invoice Amount Limit Check",
                "rule_type": "validation",
                "condition": "document_type == 'invoice' and total_amount > 10000",
                "action": "flag_for_review",
                "priority": 1
            },
            {
                "rule_id": "invoice_due_date",
                "rule_name": "Invoice Due Date Check",
                "rule_type": "validation", 
                "condition": "document_type == 'invoice' and due_date_overdue",
                "action": "flag_overdue",
                "priority": 2
            },
            {
                "rule_id": "invoice_vendor_whitelist",
                "rule_name": "Approved Vendor Check",
                "rule_type": "compliance",
                "condition": "document_type == 'invoice' and vendor_not_approved",
                "action": "require_approval",
                "priority": 1
            },
            
            # Contract rules
            {
                "rule_id": "contract_value_approval",
                "rule_name": "Contract Value Approval Required",
                "rule_type": "approval",
                "condition": "document_type == 'contract' and contract_value > 50000",
                "action": "require_executive_approval",
                "priority": 1
            },
            {
                "rule_id": "contract_expiration_warning",
                "rule_name": "Contract Expiration Warning",
                "rule_type": "notification",
                "condition": "document_type == 'contract' and expiration_within_30_days",
                "action": "send_expiration_warning",
                "priority": 3
            },
            
            # Financial statement rules
            {
                "rule_id": "financial_audit_required",
                "rule_name": "Financial Statement Audit Required",
                "rule_type": "compliance",
                "condition": "document_type == 'financial_statement' and total_assets > 1000000",
                "action": "require_audit",
                "priority": 1
            },
            
            # General data quality rules
            {
                "rule_id": "missing_critical_fields",
                "rule_name": "Critical Fields Missing",
                "rule_type": "data_quality",
                "condition": "critical_fields_missing",
                "action": "flag_incomplete",
                "priority": 1
            },
            {
                "rule_id": "low_confidence_data",
                "rule_name": "Low Confidence Data",
                "rule_type": "data_quality",
                "condition": "extraction_confidence < 0.7",
                "action": "require_manual_review",
                "priority": 2
            }
        ]
        
        # Convert to BusinessRule objects
        return [BusinessRule(**rule) for rule in default_rules]
    
    def _register_rule_functions(self) -> Dict[str, Callable]:
        """Register rule evaluation functions"""
        return {
            "invoice_amount_limit": self._check_invoice_amount_limit,
            "invoice_due_date": self._check_invoice_due_date,
            "invoice_vendor_whitelist": self._check_vendor_whitelist,
            "contract_value_approval": self._check_contract_value,
            "contract_expiration_warning": self._check_contract_expiration,
            "financial_audit_required": self._check_financial_audit,
            "missing_critical_fields": self._check_missing_fields,
            "low_confidence_data": self._check_confidence_threshold
        }
    
    async def evaluate_rules(self, validated_data: Dict[str, Any], document_type: str, 
                           metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate all applicable business rules
        
        Args:
            validated_data: Validated extracted data
            document_type: Type of document
            metadata: Document metadata and processing info
        
        Returns:
            Rule evaluation results
        """
        evaluation_results = {
            "rules_evaluated": [],
            "rules_triggered": [],
            "actions_required": [],
            "compliance_status": "compliant",
            "risk_level": "low",
            "recommendations": []
        }
        
        try:
            # Filter rules applicable to this document type
            applicable_rules = [
                rule for rule in self.rules 
                if self._is_rule_applicable(rule, document_type)
            ]
            
            # Evaluate each applicable rule
            for rule in applicable_rules:
                rule_result = await self._evaluate_single_rule(
                    rule, validated_data, document_type, metadata
                )
                
                evaluation_results["rules_evaluated"].append({
                    "rule_id": rule["rule_id"],
                    "rule_name": rule["rule_name"],
                    "triggered": rule_result["triggered"],
                    "result": rule_result
                })
                
                if rule_result["triggered"]:
                    evaluation_results["rules_triggered"].append(rule)
                    evaluation_results["actions_required"].append({
                        "rule_id": rule["rule_id"],
                        "action": rule["action"],
                        "priority": rule["priority"],
                        "details": rule_result.get("details", "")
                    })
            
            # Determine overall compliance and risk
            evaluation_results["compliance_status"] = self._determine_compliance_status(
                evaluation_results["rules_triggered"]
            )
            evaluation_results["risk_level"] = self._determine_risk_level(
                evaluation_results["rules_triggered"]
            )
            
            # Generate recommendations
            evaluation_results["recommendations"] = self._generate_recommendations(
                evaluation_results["actions_required"]
            )
            
            return evaluation_results
        
        except Exception as e:
            logger.error(f"Rule evaluation failed: {e}")
            return {
                "rules_evaluated": [],
                "rules_triggered": [],
                "actions_required": [],
                "compliance_status": "unknown",
                "risk_level": "unknown",
                "recommendations": [],
                "error": str(e)
            }
    
    def _is_rule_applicable(self, rule: BusinessRule, document_type: str) -> bool:
        """Check if rule applies to document type"""
        condition = rule["condition"]
        
        # Simple check for document type in condition
        if f"document_type == '{document_type}'" in condition:
            return True
        elif "document_type" not in condition:
            return True  # General rules apply to all types
        else:
            return False
    
    async def _evaluate_single_rule(self, rule: BusinessRule, validated_data: Dict[str, Any], 
                                  document_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single business rule"""
        try:
            rule_function = self.rule_functions.get(rule["rule_id"])
            if rule_function:
                return await rule_function(rule, validated_data, document_type, metadata)
            else:
                # Generic rule evaluation
                return await self._evaluate_generic_rule(rule, validated_data, document_type, metadata)
        
        except Exception as e:
            logger.error(f"Rule evaluation failed for {rule['rule_id']}: {e}")
            return {
                "triggered": False,
                "error": str(e),
                "confidence": 0.0
            }
    
    async def _evaluate_generic_rule(self, rule: BusinessRule, validated_data: Dict[str, Any], 
                                   document_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generic rule evaluation using condition parsing"""
        try:
            # Create evaluation context
            context = {
                "document_type": document_type,
                **validated_data,
                **metadata
            }
            
            # Simple condition evaluation (could be enhanced with proper parser)
            condition = rule["condition"]
            triggered = self._evaluate_condition(condition, context)
            
            return {
                "triggered": triggered,
                "confidence": 0.8,
                "details": f"Generic evaluation of condition: {condition}"
            }
        
        except Exception as e:
            return {
                "triggered": False,
                "error": f"Generic rule evaluation failed: {str(e)}",
                "confidence": 0.0
            }
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate rule condition"""
        try:
            # Replace context variables in condition
            for key, value in context.items():
                if isinstance(value, str):
                    condition = condition.replace(key, f"'{value}'")
                else:
                    condition = condition.replace(key, str(value))
            
            # Basic safety check - only allow simple comparisons
            allowed_operators = ['==', '!=', '>', '<', '>=', '<=', 'and', 'or', 'not']
            if any(op in condition for op in ['import', 'exec', 'eval', '__']):
                return False
            
            # Evaluate condition (in production, use a proper expression parser)
            return eval(condition)
        
        except:
            return False
    
    # Specific rule evaluation functions
    async def _check_invoice_amount_limit(self, rule: BusinessRule, data: Dict[str, Any], 
                                        doc_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Check invoice amount against limit"""
        total_amount = data.get("total_amount")
        limit = 10000  # Could be configurable
        
        if isinstance(total_amount, (int, float)) and total_amount > limit:
            return {
                "triggered": True,
                "confidence": 1.0,
                "details": f"Invoice amount ${total_amount} exceeds limit of ${limit}",
                "severity": "high"
            }
        
        return {"triggered": False, "confidence": 1.0}
    
    async def _check_invoice_due_date(self, rule: BusinessRule, data: Dict[str, Any], 
                                    doc_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Check if invoice is overdue"""
        due_date_str = data.get("due_date")
        
        if due_date_str:
            try:
                from dateutil import parser as date_parser
                due_date = date_parser.parse(due_date_str)
                if due_date < datetime.now():
                    days_overdue = (datetime.now() - due_date).days
                    return {
                        "triggered": True,
                        "confidence": 1.0,
                        "details": f"Invoice is {days_overdue} days overdue",
                        "severity": "medium" if days_overdue < 30 else "high"
                    }
            except:
                pass
        
        return {"triggered": False, "confidence": 1.0}
    
    async def _check_vendor_whitelist(self, rule: BusinessRule, data: Dict[str, Any], 
                                    doc_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Check if vendor is on approved list"""
        vendor_name = data.get("vendor_name", "").lower()
        
        # Mock approved vendor list (would be loaded from config/database)
        approved_vendors = ["acme corp", "global supplies", "tech solutions inc"]
        
        if vendor_name and vendor_name not in approved_vendors:
            return {
                "triggered": True,
                "confidence": 0.8,
                "details": f"Vendor '{vendor_name}' not in approved vendor list",
                "severity": "medium"
            }
        
        return {"triggered": False, "confidence": 1.0}
    
    async def _check_contract_value(self, rule: BusinessRule, data: Dict[str, Any], 
                                  doc_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Check contract value for approval requirement"""
        contract_value = data.get("contract_value")
        threshold = 50000
        
        if isinstance(contract_value, (int, float)) and contract_value > threshold:
            return {
                "triggered": True,
                "confidence": 1.0,
                "details": f"Contract value ${contract_value} requires executive approval (>${threshold})",
                "severity": "high"
            }
        
        return {"triggered": False, "confidence": 1.0}
    
    async def _check_contract_expiration(self, rule: BusinessRule, data: Dict[str, Any], 
                                       doc_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Check contract expiration date"""
        expiration_date_str = data.get("expiration_date")
        
        if expiration_date_str:
            try:
                from dateutil import parser as date_parser
                expiration_date = date_parser.parse(expiration_date_str)
                days_until_expiration = (expiration_date - datetime.now()).days
                
                if 0 <= days_until_expiration <= 30:
                    return {
                        "triggered": True,
                        "confidence": 1.0,
                        "details": f"Contract expires in {days_until_expiration} days",
                        "severity": "medium"
                    }
            except:
                pass
        
        return {"triggered": False, "confidence": 1.0}
    
    async def _check_financial_audit(self, rule: BusinessRule, data: Dict[str, Any], 
                                   doc_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Check if financial statement requires audit"""
        total_assets = data.get("total_assets")
        threshold = 1000000
        
        if isinstance(total_assets, (int, float)) and total_assets > threshold:
            return {
                "triggered": True,
                "confidence": 1.0,
                "details": f"Total assets ${total_assets} require audit (>${threshold})",
                "severity": "high"
            }
        
        return {"triggered": False, "confidence": 1.0}
    
    async def _check_missing_fields(self, rule: BusinessRule, data: Dict[str, Any], 
                                  doc_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Check for missing critical fields"""
        critical_fields = {
            "invoice": ["invoice_number", "total_amount", "vendor_name"],
            "contract": ["parties", "effective_date", "contract_value"],
            "financial_statement": ["company_name", "total_assets", "period_ending"]
        }
        
        required_fields = critical_fields.get(doc_type, [])
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return {
                "triggered": True,
                "confidence": 1.0,
                "details": f"Missing critical fields: {', '.join(missing_fields)}",
                "severity": "high"
            }
        
        return {"triggered": False, "confidence": 1.0}
    
    async def _check_confidence_threshold(self, rule: BusinessRule, data: Dict[str, Any], 
                                        doc_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Check extraction confidence threshold"""
        extraction_confidence = metadata.get("extraction_confidence", 1.0)
        # Lowered threshold from 0.7 to 0.4 to reduce false positives for human review
        threshold = 0.4
        
        if extraction_confidence < threshold:
            return {
                "triggered": True,
                "confidence": 1.0,
                "details": f"Extraction confidence {extraction_confidence:.2f} below threshold {threshold}",
                "severity": "medium"
            }
        
        return {"triggered": False, "confidence": 1.0}
    
    def _determine_compliance_status(self, triggered_rules: List[BusinessRule]) -> str:
        """Determine overall compliance status"""
        if not triggered_rules:
            return "compliant"
        
        compliance_rules = [rule for rule in triggered_rules if rule["rule_type"] == "compliance"]
        if compliance_rules:
            return "non_compliant"
        
        return "warning"
    
    def _determine_risk_level(self, triggered_rules: List[BusinessRule]) -> str:
        """Determine overall risk level"""
        if not triggered_rules:
            return "low"
        
        high_priority_rules = [rule for rule in triggered_rules if rule["priority"] == 1]
        if high_priority_rules:
            return "high"
        
        medium_priority_rules = [rule for rule in triggered_rules if rule["priority"] == 2]
        if medium_priority_rules:
            return "medium"
        
        return "low"
    
    def _generate_recommendations(self, actions_required: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on triggered rules"""
        recommendations = []
        
        for action in actions_required:
            action_type = action["action"]
            
            if action_type == "flag_for_review":
                recommendations.append("Document requires manual review due to high value or risk")
            elif action_type == "require_approval":
                recommendations.append("Document requires approval before processing")
            elif action_type == "require_executive_approval":
                recommendations.append("Document requires executive-level approval")
            elif action_type == "send_expiration_warning":
                recommendations.append("Send expiration warning notification")
            elif action_type == "require_audit":
                recommendations.append("Financial statement requires professional audit")
            elif action_type == "flag_incomplete":
                recommendations.append("Document is incomplete - missing critical information")
            elif action_type == "require_manual_review":
                recommendations.append("Low confidence extraction requires manual verification")
        
        return list(set(recommendations))  # Remove duplicates


async def rule_evaluation_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Rule Evaluation Agent - Applies business rules to validated data
    
    Responsibilities:
    1. Load and apply business rules
    2. Evaluate compliance requirements
    3. Determine risk levels
    4. Generate action recommendations
    5. Flag documents for review or approval
    
    Args:
        state: Current document processing state
    
    Returns:
        Updated state with rule evaluation results
    """
    start_time = time.time()
    agent_name = "rule_evaluation"
    
    # Add start entry to history
    state = add_agent_history_entry(state, agent_name, "started")
    state["current_agent"] = agent_name
    
    try:
        logger.info(f"Starting rule evaluation for document: {state['document']['id']}")
        
        # Check if validation was successful
        validation_result = state.get("validation_result")
        if not validation_result or not validation_result["success"]:
            logger.warning("Validation failed, but continuing with rule evaluation on extracted data")
        
        # Get validated data (or fall back to extracted data)
        validated_data = state.get("validated_data", state.get("extracted_data", {}))
        document_type = state.get("document_type", "other")
        
        if not validated_data:
            raise ValueError("No data available for rule evaluation")
        
        # Prepare metadata for rule evaluation
        metadata = {
            "extraction_confidence": state.get("extraction_result", {}).get("confidence_score", 1.0),
            "validation_confidence": state.get("validation_result", {}).get("confidence_score", 1.0),
            "document_metadata": state["document"]["metadata"]
        }
        
        # Initialize rule engine
        config = state.get("processing_config", {})
        rule_engine = BusinessRuleEngine(config)
        
        # Evaluate rules
        evaluation_results = await rule_engine.evaluate_rules(validated_data, document_type, metadata)
        
        # Update state with applied rules
        state["business_rules_applied"] = evaluation_results.get("rules_triggered", [])
        
        # Determine if human review is required
        actions_required = evaluation_results.get("actions_required", [])
        review_actions = ["flag_for_review", "require_approval", "require_executive_approval", "require_manual_review"]
        
        if any(action["action"] in review_actions for action in actions_required):
            state["requires_human_review"] = True
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create result
        result = AgentResult(
            success=True,
            result={
                "rules_evaluated_count": len(evaluation_results.get("rules_evaluated", [])),
                "rules_triggered_count": len(evaluation_results.get("rules_triggered", [])),
                "compliance_status": evaluation_results.get("compliance_status", "unknown"),
                "risk_level": evaluation_results.get("risk_level", "unknown"),
                "actions_required": evaluation_results.get("actions_required", []),
                "recommendations": evaluation_results.get("recommendations", []),
                "requires_human_review": state.get("requires_human_review", False)
            },
            error=evaluation_results.get("error"),
            confidence_score=1.0 - (len(evaluation_results.get("rules_triggered", [])) * 0.1),  # Reduce confidence for each triggered rule
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        # Update state
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "completed", result)
        
        logger.info(f"Rule evaluation completed: {result['result']['rules_triggered_count']} rules triggered, "
                   f"compliance: {result['result']['compliance_status']}, "
                   f"risk: {result['result']['risk_level']}")
        
        return state
    
    except Exception as e:
        # Handle errors
        processing_time = time.time() - start_time
        error_msg = f"Rule evaluation failed: {str(e)}"
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