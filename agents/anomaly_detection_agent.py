"""
Anomaly Detection Agent - Detects anomalies and unusual patterns in document data.
Sixth agent in the document processing pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import json
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd

from workflows.state_schema import (
    DocumentProcessingState, AgentResult, AnomalyDetection,
    add_agent_history_entry, update_agent_result
)

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Handles anomaly detection using multiple techniques"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize anomaly detector with configuration"""
        self.config = config
        self.anomaly_threshold = config.get("anomaly_threshold", 0.7)
        self.detection_methods = ["statistical", "rule_based", "ml_based"]
    
    async def detect_anomalies(self, validated_data: Dict[str, Any], document_type: str, 
                             historical_data: Optional[List[Dict[str, Any]]] = None) -> List[AnomalyDetection]:
        """
        Detect anomalies in document data
        
        Args:
            validated_data: Validated extracted data
            document_type: Type of document
            historical_data: Historical data for comparison (optional)
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        try:
            # Statistical anomaly detection
            statistical_anomalies = await self._detect_statistical_anomalies(
                validated_data, document_type
            )
            anomalies.extend(statistical_anomalies)
            
            # Rule-based anomaly detection
            rule_based_anomalies = await self._detect_rule_based_anomalies(
                validated_data, document_type
            )
            anomalies.extend(rule_based_anomalies)
            
            # ML-based anomaly detection (if historical data available)
            if historical_data and len(historical_data) > 10:
                ml_anomalies = await self._detect_ml_anomalies(
                    validated_data, document_type, historical_data
                )
                anomalies.extend(ml_anomalies)
            
            # Pattern-based anomaly detection
            pattern_anomalies = await self._detect_pattern_anomalies(
                validated_data, document_type
            )
            anomalies.extend(pattern_anomalies)
            
            # Remove duplicates and sort by severity
            unique_anomalies = self._deduplicate_anomalies(anomalies)
            return sorted(unique_anomalies, key=lambda x: self._severity_priority(x["severity"]))
        
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return [{
                "anomaly_type": "detection_error",
                "severity": "medium",
                "description": f"Anomaly detection process failed: {str(e)}",
                "confidence": 0.5,
                "affected_fields": []
            }]
    
    async def _detect_statistical_anomalies(self, data: Dict[str, Any], doc_type: str) -> List[AnomalyDetection]:
        """Detect statistical anomalies in numeric fields"""
        anomalies = []
        
        # Define expected ranges for different document types
        expected_ranges = {
            "invoice": {
                "total_amount": (0, 100000),
                "tax_amount": (0, 10000),
                "subtotal": (0, 90000)
            },
            "contract": {
                "contract_value": (0, 10000000)
            },
            "financial_statement": {
                "total_assets": (0, 1000000000),
                "total_liabilities": (0, 1000000000),
                "revenue": (0, 1000000000)
            }
        }
        
        ranges = expected_ranges.get(doc_type, {})
        
        for field_name, (min_val, max_val) in ranges.items():
            field_value = data.get(field_name)
            
            if isinstance(field_value, (int, float)):
                if field_value < min_val or field_value > max_val:
                    severity = "high" if field_value < 0 or field_value > max_val * 2 else "medium"
                    anomalies.append({
                        "anomaly_type": "statistical_outlier",
                        "severity": severity,
                        "description": f"{field_name} value {field_value} is outside expected range ({min_val}-{max_val})",
                        "confidence": 0.8,
                        "affected_fields": [field_name]
                    })
        
        return anomalies
    
    async def _detect_rule_based_anomalies(self, data: Dict[str, Any], doc_type: str) -> List[AnomalyDetection]:
        """Detect anomalies using business logic rules"""
        anomalies = []
        
        try:
            if doc_type == "invoice":
                anomalies.extend(await self._detect_invoice_anomalies(data))
            elif doc_type == "contract":
                anomalies.extend(await self._detect_contract_anomalies(data))
            elif doc_type == "financial_statement":
                anomalies.extend(await self._detect_financial_anomalies(data))
            
            # General anomalies for all document types
            anomalies.extend(await self._detect_general_anomalies(data))
        
        except Exception as e:
            logger.error(f"Rule-based anomaly detection failed: {e}")
        
        return anomalies
    
    async def _detect_invoice_anomalies(self, data: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect invoice-specific anomalies"""
        anomalies = []
        
        # Check for negative amounts
        amount_fields = ["total_amount", "subtotal", "tax_amount"]
        for field in amount_fields:
            value = data.get(field)
            if isinstance(value, (int, float)) and value < 0:
                anomalies.append({
                    "anomaly_type": "negative_amount",
                    "severity": "high",
                    "description": f"Negative {field}: {value}",
                    "confidence": 0.9,
                    "affected_fields": [field]
                })
        
        # Check tax rate reasonableness
        subtotal = data.get("subtotal")
        tax_amount = data.get("tax_amount")
        if isinstance(subtotal, (int, float)) and isinstance(tax_amount, (int, float)) and subtotal > 0:
            tax_rate = (tax_amount / subtotal) * 100
            if tax_rate > 50:  # Tax rate over 50%
                anomalies.append({
                    "anomaly_type": "unusual_tax_rate",
                    "severity": "medium",
                    "description": f"Unusually high tax rate: {tax_rate:.1f}%",
                    "confidence": 0.7,
                    "affected_fields": ["tax_amount", "subtotal"]
                })
        
        # Check for round numbers (potential manual entry)
        total_amount = data.get("total_amount")
        if isinstance(total_amount, (int, float)) and total_amount % 100 == 0 and total_amount > 1000:
            anomalies.append({
                "anomaly_type": "round_number",
                "severity": "low",
                "description": f"Total amount is a round number: {total_amount}",
                "confidence": 0.5,
                "affected_fields": ["total_amount"]
            })
        
        return anomalies
    
    async def _detect_contract_anomalies(self, data: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect contract-specific anomalies"""
        anomalies = []
        
        # Check for very short or long contract durations
        effective_date_str = data.get("effective_date")
        expiration_date_str = data.get("expiration_date")
        
        if effective_date_str and expiration_date_str:
            try:
                from dateutil import parser as date_parser
                effective_date = date_parser.parse(effective_date_str)
                expiration_date = date_parser.parse(expiration_date_str)
                duration_days = (expiration_date - effective_date).days
                
                if duration_days < 30:  # Very short contract
                    anomalies.append({
                        "anomaly_type": "short_contract_duration",
                        "severity": "medium",
                        "description": f"Very short contract duration: {duration_days} days",
                        "confidence": 0.7,
                        "affected_fields": ["effective_date", "expiration_date"]
                    })
                elif duration_days > 3650:  # Over 10 years
                    anomalies.append({
                        "anomaly_type": "long_contract_duration",
                        "severity": "medium",
                        "description": f"Very long contract duration: {duration_days} days ({duration_days/365:.1f} years)",
                        "confidence": 0.7,
                        "affected_fields": ["effective_date", "expiration_date"]
                    })
            except:
                pass
        
        # Check for unusual contract values
        contract_value = data.get("contract_value")
        if isinstance(contract_value, (int, float)):
            if contract_value == 0:
                anomalies.append({
                    "anomaly_type": "zero_value_contract",
                    "severity": "medium",
                    "description": "Contract has zero value",
                    "confidence": 0.8,
                    "affected_fields": ["contract_value"]
                })
        
        return anomalies
    
    async def _detect_financial_anomalies(self, data: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect financial statement anomalies"""
        anomalies = []
        
        # Check accounting equation: Assets = Liabilities + Equity
        assets = data.get("total_assets")
        liabilities = data.get("total_liabilities")
        equity = data.get("total_equity")
        
        if all(isinstance(x, (int, float)) for x in [assets, liabilities, equity]):
            difference = abs(assets - (liabilities + equity))
            tolerance = max(assets * 0.01, 1000)  # 1% or $1000 tolerance
            
            if difference > tolerance:
                anomalies.append({
                    "anomaly_type": "accounting_equation_imbalance",
                    "severity": "high",
                    "description": f"Accounting equation imbalance: Assets ({assets}) != Liabilities ({liabilities}) + Equity ({equity})",
                    "confidence": 0.9,
                    "affected_fields": ["total_assets", "total_liabilities", "total_equity"]
                })
        
        # Check for negative equity
        if isinstance(equity, (int, float)) and equity < 0:
            anomalies.append({
                "anomaly_type": "negative_equity",
                "severity": "high",
                "description": f"Negative equity: {equity}",
                "confidence": 0.9,
                "affected_fields": ["total_equity"]
            })
        
        return anomalies
    
    async def _detect_general_anomalies(self, data: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect general anomalies applicable to all document types"""
        anomalies = []
        
        # Check for suspicious patterns in text fields
        text_fields = [k for k, v in data.items() if isinstance(v, str)]
        
        for field in text_fields:
            value = data[field]
            
            # Check for repeated characters (potential OCR error)
            if len(set(value)) < len(value) * 0.3 and len(value) > 10:
                anomalies.append({
                    "anomaly_type": "repeated_characters",
                    "severity": "low",
                    "description": f"Field {field} has many repeated characters, possible OCR error",
                    "confidence": 0.6,
                    "affected_fields": [field]
                })
            
            # Check for unusual character patterns
            if len(value) > 5 and value.count('X') > len(value) * 0.5:
                anomalies.append({
                    "anomaly_type": "placeholder_text",
                    "severity": "medium",
                    "description": f"Field {field} appears to contain placeholder text",
                    "confidence": 0.7,
                    "affected_fields": [field]
                })
        
        # Check for missing critical data
        non_null_fields = [k for k, v in data.items() if v is not None and v != ""]
        if len(non_null_fields) < 3:
            anomalies.append({
                "anomaly_type": "insufficient_data",
                "severity": "high",
                "description": f"Very few fields extracted: only {len(non_null_fields)} non-null fields",
                "confidence": 0.8,
                "affected_fields": list(data.keys())
            })
        
        return anomalies
    
    async def _detect_ml_anomalies(self, data: Dict[str, Any], doc_type: str, 
                                 historical_data: List[Dict[str, Any]]) -> List[AnomalyDetection]:
        """Detect anomalies using machine learning (Isolation Forest)"""
        anomalies = []
        
        try:
            # Prepare data for ML model
            numeric_fields = self._get_numeric_fields(data, historical_data)
            if len(numeric_fields) < 2:
                return anomalies  # Need at least 2 numeric fields
            
            # Create feature matrix
            feature_matrix = []
            field_names = list(numeric_fields.keys())
            
            # Add historical data
            for hist_data in historical_data:
                row = [hist_data.get(field, 0) for field in field_names]
                feature_matrix.append(row)
            
            # Add current data
            current_row = [data.get(field, 0) for field in field_names]
            feature_matrix.append(current_row)
            
            if len(feature_matrix) < 10:  # Need sufficient historical data
                return anomalies
            
            # Prepare data
            X = np.array(feature_matrix)
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train Isolation Forest
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            predictions = iso_forest.fit_predict(X_scaled)
            scores = iso_forest.score_samples(X_scaled)
            
            # Check if current document is anomalous
            current_prediction = predictions[-1]
            current_score = scores[-1]
            
            if current_prediction == -1:  # Anomaly detected
                anomalies.append({
                    "anomaly_type": "ml_statistical_outlier",
                    "severity": "medium" if current_score > -0.5 else "high",
                    "description": f"Document data is statistically anomalous compared to historical patterns (score: {current_score:.3f})",
                    "confidence": min(0.9, abs(current_score)),
                    "affected_fields": field_names
                })
        
        except Exception as e:
            logger.error(f"ML anomaly detection failed: {e}")
        
        return anomalies
    
    async def _detect_pattern_anomalies(self, data: Dict[str, Any], doc_type: str) -> List[AnomalyDetection]:
        """Detect pattern-based anomalies"""
        anomalies = []
        
        # Check for inconsistent date formats
        date_fields = [k for k, v in data.items() if isinstance(v, str) and 'date' in k.lower()]
        date_formats = []
        
        for field in date_fields:
            value = data[field]
            if value:
                # Simple pattern detection
                if '/' in value:
                    date_formats.append('slash')
                elif '-' in value:
                    date_formats.append('dash')
                elif '.' in value:
                    date_formats.append('dot')
        
        if len(set(date_formats)) > 1:
            anomalies.append({
                "anomaly_type": "inconsistent_date_formats",
                "severity": "low",
                "description": f"Inconsistent date formats detected: {set(date_formats)}",
                "confidence": 0.6,
                "affected_fields": date_fields
            })
        
        return anomalies
    
    def _get_numeric_fields(self, data: Dict[str, Any], historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract numeric fields common across current and historical data"""
        numeric_fields = {}
        
        # Find fields that are numeric in current data
        for key, value in data.items():
            if isinstance(value, (int, float)):
                # Check if this field exists in historical data
                if any(key in hist_data and isinstance(hist_data.get(key), (int, float)) 
                      for hist_data in historical_data):
                    numeric_fields[key] = value
        
        return numeric_fields
    
    def _deduplicate_anomalies(self, anomalies: List[AnomalyDetection]) -> List[AnomalyDetection]:
        """Remove duplicate anomalies"""
        seen = set()
        unique_anomalies = []
        
        for anomaly in anomalies:
            # Create a key based on type and affected fields
            key = (anomaly["anomaly_type"], tuple(sorted(anomaly["affected_fields"])))
            if key not in seen:
                seen.add(key)
                unique_anomalies.append(anomaly)
        
        return unique_anomalies
    
    def _severity_priority(self, severity: str) -> int:
        """Get priority number for severity (lower = higher priority)"""
        priorities = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return priorities.get(severity, 4)


async def anomaly_detection_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Anomaly Detection Agent - Detects anomalies and unusual patterns
    
    Responsibilities:
    1. Detect statistical anomalies in numeric data
    2. Apply rule-based anomaly detection
    3. Use ML-based detection when historical data available
    4. Identify pattern inconsistencies
    5. Flag suspicious or unusual data patterns
    
    Args:
        state: Current document processing state
    
    Returns:
        Updated state with anomaly detection results
    """
    start_time = time.time()
    agent_name = "anomaly_detection"
    
    # Add start entry to history
    state = add_agent_history_entry(state, agent_name, "started")
    state["current_agent"] = agent_name
    
    try:
        logger.info(f"Starting anomaly detection for document: {state['document']['id']}")
        
        # Get validated data (or fall back to extracted data)
        validated_data = state.get("validated_data", state.get("extracted_data", {}))
        document_type = state.get("document_type", "other")
        
        if not validated_data:
            raise ValueError("No data available for anomaly detection")
        
        # Initialize anomaly detector
        config = state.get("processing_config", {})
        detector = AnomalyDetector(config)
        
        # Perform anomaly detection
        # Note: In a real implementation, you would load historical data from a database
        historical_data = []  # Placeholder for historical data
        
        detected_anomalies = await detector.detect_anomalies(
            validated_data, document_type, historical_data
        )
        
        # Update state with detected anomalies
        state["anomalies_detected"] = detected_anomalies
        
        # Determine if anomalies require human review
        high_severity_anomalies = [a for a in detected_anomalies if a["severity"] in ["critical", "high"]]
        if high_severity_anomalies:
            state["requires_human_review"] = True
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Calculate confidence score (lower confidence if more anomalies detected)
        confidence_score = max(0.1, 1.0 - (len(detected_anomalies) * 0.1))
        
        # Create result
        result = AgentResult(
            success=True,
            result={
                "anomalies_detected_count": len(detected_anomalies),
                "high_severity_count": len([a for a in detected_anomalies if a["severity"] == "high"]),
                "critical_severity_count": len([a for a in detected_anomalies if a["severity"] == "critical"]),
                "anomaly_types": list(set(a["anomaly_type"] for a in detected_anomalies)),
                "requires_human_review": state.get("requires_human_review", False),
                "anomalies": detected_anomalies
            },
            error=None,
            confidence_score=confidence_score,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        # Update state
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "completed", result)
        
        logger.info(f"Anomaly detection completed: {len(detected_anomalies)} anomalies detected "
                   f"({len(high_severity_anomalies)} high/critical severity)")
        
        return state
    
    except Exception as e:
        # Handle errors
        processing_time = time.time() - start_time
        error_msg = f"Anomaly detection failed: {str(e)}"
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