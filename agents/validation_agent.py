"""
Validation Agent - Validates extracted data quality and consistency.
Fourth agent in the document processing pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import re
from dateutil import parser as date_parser

from workflows.state_schema import DocumentProcessingState, AgentResult, add_agent_history_entry, update_agent_result

logger = logging.getLogger(__name__)


class DataValidator:
    """Handles data validation and quality checks"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize validator with configuration"""
        self.config = config
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for different field types"""
        return {
            "email": {
                "pattern": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                "required": False
            },
            "phone": {
                "pattern": r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',
                "required": False
            },
            "date": {
                "format_check": True,
                "future_check": False,
                "required": False
            },
            "number": {
                "min_value": None,
                "max_value": None,
                "decimal_places": None,
                "required": False
            },
            "string": {
                "min_length": 1,
                "max_length": 1000,
                "required": False
            },
            "array": {
                "min_items": 0,
                "max_items": 100,
                "required": False
            }
        }
    
    async def validate_extracted_data(self, extracted_data: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """
        Validate extracted data
        
        Args:
            extracted_data: Data extracted by extraction agent
            document_type: Type of document
        
        Returns:
            Validation results with errors and corrected data
        """
        validation_results = {
            "is_valid": True,
            "validation_errors": [],
            "validation_warnings": [],
            "corrected_data": {},
            "field_validations": {},
            "overall_confidence": 1.0
        }
        
        try:
            # Validate each field
            for field_name, field_value in extracted_data.items():
                field_validation = await self._validate_field(field_name, field_value, document_type)
                validation_results["field_validations"][field_name] = field_validation
                
                # Collect errors and warnings
                if field_validation["errors"]:
                    validation_results["validation_errors"].extend(field_validation["errors"])
                    validation_results["is_valid"] = False
                
                if field_validation["warnings"]:
                    validation_results["validation_warnings"].extend(field_validation["warnings"])
                
                # Use corrected value if available
                validation_results["corrected_data"][field_name] = field_validation.get("corrected_value", field_value)
            
            # Perform cross-field validation
            cross_validation = await self._cross_field_validation(extracted_data, document_type)
            validation_results["validation_errors"].extend(cross_validation["errors"])
            validation_results["validation_warnings"].extend(cross_validation["warnings"])
            
            if cross_validation["errors"]:
                validation_results["is_valid"] = False
            
            # Calculate overall confidence
            validation_results["overall_confidence"] = self._calculate_validation_confidence(validation_results)
            
            return validation_results
        
        except Exception as e:
            logger.error(f"Validation process failed: {e}")
            return {
                "is_valid": False,
                "validation_errors": [f"Validation process failed: {str(e)}"],
                "validation_warnings": [],
                "corrected_data": extracted_data,
                "field_validations": {},
                "overall_confidence": 0.0
            }
    
    async def _validate_field(self, field_name: str, field_value: Any, document_type: str) -> Dict[str, Any]:
        """Validate individual field"""
        field_validation = {
            "field_name": field_name,
            "original_value": field_value,
            "corrected_value": field_value,
            "errors": [],
            "warnings": [],
            "confidence": 1.0
        }
        
        # Skip validation for None values
        if field_value is None:
            return field_validation
        
        try:
            # Determine field type from name and value
            field_type = self._infer_field_type(field_name, field_value)
            
            # Apply type-specific validation
            if field_type == "email":
                field_validation.update(await self._validate_email(field_value))
            elif field_type == "phone":
                field_validation.update(await self._validate_phone(field_value))
            elif field_type == "date":
                field_validation.update(await self._validate_date(field_value))
            elif field_type == "number":
                field_validation.update(await self._validate_number(field_value))
            elif field_type == "string":
                field_validation.update(await self._validate_string(field_value))
            elif field_type == "array":
                field_validation.update(await self._validate_array(field_value))
            
            return field_validation
        
        except Exception as e:
            field_validation["errors"].append(f"Field validation failed: {str(e)}")
            field_validation["confidence"] = 0.0
            return field_validation
    
    def _infer_field_type(self, field_name: str, field_value: Any) -> str:
        """Infer field type from name and value"""
        field_name_lower = field_name.lower()
        
        if "email" in field_name_lower:
            return "email"
        elif "phone" in field_name_lower or "tel" in field_name_lower:
            return "phone"
        elif "date" in field_name_lower or "time" in field_name_lower:
            return "date"
        elif "amount" in field_name_lower or "total" in field_name_lower or "price" in field_name_lower:
            return "number"
        elif isinstance(field_value, list):
            return "array"
        elif isinstance(field_value, (int, float)):
            return "number"
        else:
            return "string"
    
    async def _validate_email(self, email: str) -> Dict[str, Any]:
        """Validate email format"""
        result = {"errors": [], "warnings": [], "confidence": 1.0}
        
        if not isinstance(email, str):
            result["errors"].append("Email must be a string")
            result["confidence"] = 0.0
            return result
        
        email_pattern = self.validation_rules["email"]["pattern"]
        if not re.match(email_pattern, email.strip()):
            result["errors"].append(f"Invalid email format: {email}")
            result["confidence"] = 0.2
        else:
            result["corrected_value"] = email.strip().lower()
        
        return result
    
    async def _validate_phone(self, phone: str) -> Dict[str, Any]:
        """Validate phone number format"""
        result = {"errors": [], "warnings": [], "confidence": 1.0}
        
        if not isinstance(phone, str):
            result["errors"].append("Phone number must be a string")
            result["confidence"] = 0.0
            return result
        
        # Clean phone number
        cleaned_phone = re.sub(r'[^\d+]', '', phone)
        
        if len(cleaned_phone) < 10:
            result["errors"].append(f"Phone number too short: {phone}")
            result["confidence"] = 0.3
        elif len(cleaned_phone) > 15:
            result["warnings"].append(f"Phone number unusually long: {phone}")
            result["confidence"] = 0.7
        else:
            result["corrected_value"] = cleaned_phone
        
        return result
    
    async def _validate_date(self, date_value: str) -> Dict[str, Any]:
        """Validate date format and value"""
        result = {"errors": [], "warnings": [], "confidence": 1.0}
        
        if not isinstance(date_value, str):
            result["errors"].append("Date must be a string")
            result["confidence"] = 0.0
            return result
        
        try:
            parsed_date = date_parser.parse(date_value)
            result["corrected_value"] = parsed_date.strftime("%Y-%m-%d")
            
            # Check if date is reasonable (not too far in future/past)
            current_year = datetime.now().year
            if parsed_date.year < 1900 or parsed_date.year > current_year + 10:
                result["warnings"].append(f"Date seems unusual: {date_value}")
                result["confidence"] = 0.7
        
        except (ValueError, TypeError) as e:
            result["errors"].append(f"Invalid date format: {date_value}")
            result["confidence"] = 0.1
        
        return result
    
    async def _validate_number(self, number_value: Any) -> Dict[str, Any]:
        """Validate numeric value"""
        result = {"errors": [], "warnings": [], "confidence": 1.0}
        
        try:
            if isinstance(number_value, str):
                # Try to convert string to number
                cleaned_number = re.sub(r'[^\d.-]', '', number_value)
                if cleaned_number:
                    number_value = float(cleaned_number)
                else:
                    raise ValueError("No numeric content found")
            
            if not isinstance(number_value, (int, float)):
                result["errors"].append("Value is not numeric")
                result["confidence"] = 0.0
                return result
            
            result["corrected_value"] = number_value
            
            # Check for reasonable ranges (context-dependent)
            if number_value < 0:
                result["warnings"].append("Negative value detected")
                result["confidence"] = 0.8
            elif number_value > 1000000000:  # 1 billion
                result["warnings"].append("Very large number detected")
                result["confidence"] = 0.8
        
        except (ValueError, TypeError) as e:
            result["errors"].append(f"Invalid number format: {number_value}")
            result["confidence"] = 0.1
        
        return result
    
    async def _validate_string(self, string_value: str) -> Dict[str, Any]:
        """Validate string value"""
        result = {"errors": [], "warnings": [], "confidence": 1.0}
        
        if not isinstance(string_value, str):
            result["errors"].append("Value must be a string")
            result["confidence"] = 0.0
            return result
        
        # Clean string
        cleaned_string = string_value.strip()
        result["corrected_value"] = cleaned_string
        
        if len(cleaned_string) == 0:
            result["warnings"].append("Empty string value")
            result["confidence"] = 0.5
        elif len(cleaned_string) > 1000:
            result["warnings"].append("Very long string value")
            result["confidence"] = 0.8
        
        return result
    
    async def _validate_array(self, array_value: List[Any]) -> Dict[str, Any]:
        """Validate array value"""
        result = {"errors": [], "warnings": [], "confidence": 1.0}
        
        if not isinstance(array_value, list):
            result["errors"].append("Value must be an array")
            result["confidence"] = 0.0
            return result
        
        if len(array_value) == 0:
            result["warnings"].append("Empty array")
            result["confidence"] = 0.7
        elif len(array_value) > 100:
            result["warnings"].append("Very large array")
            result["confidence"] = 0.8
        
        return result
    
    async def _cross_field_validation(self, extracted_data: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """Perform cross-field validation"""
        result = {"errors": [], "warnings": []}
        
        try:
            # Document type specific validations
            if document_type == "invoice":
                await self._validate_invoice_fields(extracted_data, result)
            elif document_type == "contract":
                await self._validate_contract_fields(extracted_data, result)
            elif document_type == "financial_statement":
                await self._validate_financial_fields(extracted_data, result)
        
        except Exception as e:
            result["errors"].append(f"Cross-field validation failed: {str(e)}")
        
        return result
    
    async def _validate_invoice_fields(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate invoice-specific field relationships"""
        # Check if subtotal + tax = total
        subtotal = data.get("subtotal")
        tax_amount = data.get("tax_amount")
        total_amount = data.get("total_amount")
        
        if all(isinstance(x, (int, float)) for x in [subtotal, tax_amount, total_amount]):
            calculated_total = subtotal + tax_amount
            if abs(calculated_total - total_amount) > 0.01:  # Allow for rounding
                result["warnings"].append(f"Total amount mismatch: {total_amount} vs calculated {calculated_total}")
        
        # Check date consistency
        invoice_date = data.get("invoice_date")
        due_date = data.get("due_date")
        
        if invoice_date and due_date:
            try:
                inv_date = date_parser.parse(invoice_date)
                due_date_parsed = date_parser.parse(due_date)
                if due_date_parsed < inv_date:
                    result["errors"].append("Due date cannot be before invoice date")
            except:
                pass  # Date parsing already handled in field validation
    
    async def _validate_contract_fields(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate contract-specific field relationships"""
        effective_date = data.get("effective_date")
        expiration_date = data.get("expiration_date")
        
        if effective_date and expiration_date:
            try:
                eff_date = date_parser.parse(effective_date)
                exp_date = date_parser.parse(expiration_date)
                if exp_date <= eff_date:
                    result["errors"].append("Expiration date must be after effective date")
            except:
                pass
    
    async def _validate_financial_fields(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Validate financial statement field relationships"""
        assets = data.get("total_assets")
        liabilities = data.get("total_liabilities")
        equity = data.get("total_equity")
        
        if all(isinstance(x, (int, float)) for x in [assets, liabilities, equity]):
            if abs(assets - (liabilities + equity)) > 0.01:  # Basic accounting equation
                result["warnings"].append("Assets != Liabilities + Equity (accounting equation)")
    
    def _calculate_validation_confidence(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall validation confidence"""
        if not validation_results["field_validations"]:
            return 0.0
        
        field_confidences = [
            field_val.get("confidence", 0.0) 
            for field_val in validation_results["field_validations"].values()
        ]
        
        avg_confidence = sum(field_confidences) / len(field_confidences)
        
        # Reduce confidence based on errors
        error_count = len(validation_results["validation_errors"])
        warning_count = len(validation_results["validation_warnings"])
        
        confidence_penalty = (error_count * 0.2) + (warning_count * 0.1)
        final_confidence = max(0.0, avg_confidence - confidence_penalty)
        
        return min(1.0, final_confidence)


async def validation_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Validation Agent - Validates extracted data quality and consistency
    
    Responsibilities:
    1. Validate individual field formats and values
    2. Perform cross-field validation
    3. Correct common data issues
    4. Calculate validation confidence scores
    5. Flag data quality issues
    
    Args:
        state: Current document processing state
    
    Returns:
        Updated state with validation results
    """
    start_time = time.time()
    agent_name = "validation"
    
    # Add start entry to history
    state = add_agent_history_entry(state, agent_name, "started")
    state["current_agent"] = agent_name
    
    try:
        logger.info(f"Starting validation for document: {state['document']['id']}")
        
        # Check if extraction was successful
        extraction_result = state.get("extraction_result")
        if not extraction_result or not extraction_result["success"]:
            raise ValueError("Cannot validate data: extraction failed or incomplete")
        
        # Get extracted data
        extracted_data = state.get("extracted_data", {})
        document_type = state.get("document_type", "other")
        
        if not extracted_data:
            raise ValueError("No extracted data available for validation")
        
        # Initialize validator
        config = state.get("processing_config", {})
        validator = DataValidator(config)
        
        # Perform validation
        validation_results = await validator.validate_extracted_data(extracted_data, document_type)
        
        # Update validated data in state
        state["validated_data"] = validation_results["corrected_data"]
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create result
        result = AgentResult(
            success=validation_results["is_valid"],
            result={
                "is_valid": validation_results["is_valid"],
                "validation_errors": validation_results["validation_errors"],
                "validation_warnings": validation_results["validation_warnings"],
                "field_validations": validation_results["field_validations"],
                "corrected_fields": len([k for k, v in validation_results["field_validations"].items() 
                                       if v.get("corrected_value") != v.get("original_value")]),
                "total_fields": len(validation_results["field_validations"]),
                "error_count": len(validation_results["validation_errors"]),
                "warning_count": len(validation_results["validation_warnings"])
            },
            error=None if validation_results["is_valid"] else "Data validation failed",
            confidence_score=validation_results["overall_confidence"],
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        # Update state
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "completed", result)
        
        logger.info(f"Validation completed: {result['result']['error_count']} errors, "
                   f"{result['result']['warning_count']} warnings "
                   f"(confidence: {result['confidence_score']:.2f})")
        
        return state
    
    except Exception as e:
        # Handle errors
        processing_time = time.time() - start_time
        error_msg = f"Validation failed: {str(e)}"
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