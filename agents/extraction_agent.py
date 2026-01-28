"""
Extraction Agent - Extracts structured data from documents using LLM.
Third agent in the document processing pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import re

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from workflows.state_schema import DocumentProcessingState, AgentResult, add_agent_history_entry, update_agent_result

logger = logging.getLogger(__name__)


# Extraction schemas for different document types
EXTRACTION_SCHEMAS = {
    "invoice": {
        "fields": {
            "invoice_number": {"type": "string", "description": "Invoice number or ID"},
            "invoice_date": {"type": "date", "description": "Date of invoice"},
            "due_date": {"type": "date", "description": "Payment due date"},
            "vendor_name": {"type": "string", "description": "Name of vendor/supplier"},
            "vendor_address": {"type": "string", "description": "Vendor address"},
            "customer_name": {"type": "string", "description": "Customer/buyer name"},
            "customer_address": {"type": "string", "description": "Customer address"},
            "line_items": {"type": "array", "description": "List of invoice line items"},
            "subtotal": {"type": "number", "description": "Subtotal amount"},
            "tax_amount": {"type": "number", "description": "Tax amount"},
            "total_amount": {"type": "number", "description": "Total amount due"},
            "currency": {"type": "string", "description": "Currency code"},
            "payment_terms": {"type": "string", "description": "Payment terms"}
        }
    },
    "contract": {
        "fields": {
            "contract_title": {"type": "string", "description": "Title of the contract"},
            "parties": {"type": "array", "description": "List of contracting parties"},
            "effective_date": {"type": "date", "description": "Contract effective date"},
            "expiration_date": {"type": "date", "description": "Contract expiration date"},
            "contract_value": {"type": "number", "description": "Total contract value"},
            "key_terms": {"type": "array", "description": "Key contract terms"},
            "governing_law": {"type": "string", "description": "Governing law jurisdiction"},
            "signatures": {"type": "array", "description": "Signature information"},
            "renewal_terms": {"type": "string", "description": "Renewal terms if any"}
        }
    },
    "resume": {
        "fields": {
            "full_name": {"type": "string", "description": "Full name of candidate"},
            "email": {"type": "string", "description": "Email address"},
            "phone": {"type": "string", "description": "Phone number"},
            "address": {"type": "string", "description": "Address"},
            "work_experience": {"type": "array", "description": "Work experience entries"},
            "education": {"type": "array", "description": "Education entries"},
            "skills": {"type": "array", "description": "Skills and competencies"},
            "certifications": {"type": "array", "description": "Certifications"},
            "languages": {"type": "array", "description": "Languages spoken"},
            "summary": {"type": "string", "description": "Professional summary"}
        }
    },
    "financial_statement": {
        "fields": {
            "company_name": {"type": "string", "description": "Company name"},
            "statement_type": {"type": "string", "description": "Type of financial statement"},
            "period_ending": {"type": "date", "description": "Period ending date"},
            "total_assets": {"type": "number", "description": "Total assets"},
            "total_liabilities": {"type": "number", "description": "Total liabilities"},
            "total_equity": {"type": "number", "description": "Total equity"},
            "revenue": {"type": "number", "description": "Total revenue"},
            "net_income": {"type": "number", "description": "Net income"},
            "cash_flow": {"type": "number", "description": "Cash flow"},
            "currency": {"type": "string", "description": "Currency"}
        }
    },
    "medical_record": {
        "fields": {
            "patient_name": {"type": "string", "description": "Patient full name"},
            "patient_id": {"type": "string", "description": "Patient ID or MRN"},
            "date_of_birth": {"type": "date", "description": "Patient date of birth"},
            "visit_date": {"type": "date", "description": "Visit or record date"},
            "diagnosis": {"type": "array", "description": "Diagnoses"},
            "medications": {"type": "array", "description": "Medications prescribed"},
            "procedures": {"type": "array", "description": "Procedures performed"},
            "physician": {"type": "string", "description": "Attending physician"},
            "vital_signs": {"type": "object", "description": "Vital signs measurements"}
        }
    },
    "email": {
        "fields": {
            "sender": {"type": "string", "description": "Email sender"},
            "recipients": {"type": "array", "description": "Email recipients"},
            "subject": {"type": "string", "description": "Email subject"},
            "date_sent": {"type": "datetime", "description": "Date and time sent"},
            "body": {"type": "string", "description": "Email body content"},
            "attachments": {"type": "array", "description": "Attachment names"},
            "priority": {"type": "string", "description": "Email priority"},
            "thread_id": {"type": "string", "description": "Email thread ID"}
        }
    },
    "other": {
        "fields": {
            "title": {"type": "string", "description": "Document title"},
            "author": {"type": "string", "description": "Document author"},
            "date": {"type": "date", "description": "Document date"},
            "key_points": {"type": "array", "description": "Key points or topics"},
            "summary": {"type": "string", "description": "Document summary"}
        }
    }
}


class DataExtractor:
    """Handles structured data extraction using LLM"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        """Initialize extractor with LLM configuration"""
        self.llm_config = llm_config
        self.llm = self._create_llm()
    
    def _create_llm(self):
        """Create LLM instance based on configuration"""
        provider = self.llm_config.get("provider", "openai")
        model = self.llm_config.get("model", "gpt-4")
        temperature = self.llm_config.get("temperature", 0.1)
        max_tokens = self.llm_config.get("max_tokens", 2000)
        
        if provider == "openai":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    async def extract_data(self, content: str, document_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from document content
        
        Args:
            content: Document content
            document_type: Type of document
            metadata: Document metadata
        
        Returns:
            Extracted structured data
        """
        try:
            # Get extraction schema for document type
            schema = EXTRACTION_SCHEMAS.get(document_type, EXTRACTION_SCHEMAS["other"])
            
            # Create extraction prompt
            prompt = self._create_extraction_prompt(content, document_type, schema, metadata)
            
            # Get LLM response
            response = await self.llm.ainvoke(prompt)
            
            # Parse response
            result = self._parse_extraction_response(response.content, schema)
            
            return result
        
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Fallback to rule-based extraction
            return self._fallback_extraction(content, document_type, metadata)
    
    def _create_extraction_prompt(self, content: str, document_type: str, schema: Dict[str, Any], metadata: Dict[str, Any]) -> List:
        """Create extraction prompt for LLM"""
        
        # Truncate content if too long
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "... [truncated]"
        
        # Create field descriptions
        field_descriptions = []
        for field_name, field_info in schema["fields"].items():
            field_descriptions.append(f"- {field_name} ({field_info['type']}): {field_info['description']}")
        
        system_message = SystemMessage(content=f"""
You are a data extraction expert. Your task is to extract structured information from a {document_type} document.

Extract the following fields:
{chr(10).join(field_descriptions)}

Instructions:
1. Extract only information that is explicitly present in the document
2. Use null for fields that are not found or unclear
3. For dates, use ISO format (YYYY-MM-DD) or (YYYY-MM-DD HH:MM:SS) for datetime
4. For arrays, provide a list of items
5. For numbers, extract numeric values without currency symbols
6. Be precise and accurate - don't infer information that isn't clearly stated

Respond with a JSON object containing the extracted fields. Include a "confidence" field (0.0-1.0) indicating your confidence in the extraction accuracy.
""")
        
        human_message = HumanMessage(content=f"""
Extract structured data from this {document_type} document:

METADATA:
- File type: {metadata.get('file_type', 'unknown')}
- Content length: {metadata.get('content_length', 0)} characters

CONTENT:
{content}

Please extract the requested fields and provide the result as a JSON object with a confidence score.
""")
        
        return [system_message, human_message]
    
    def _parse_extraction_response(self, response: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM extraction response"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Validate and clean extracted data
                cleaned_result = self._validate_extracted_data(result, schema)
                
                return cleaned_result
            
            else:
                raise ValueError("No JSON found in response")
        
        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}")
            return {
                "extraction_success": False,
                "error": f"Failed to parse LLM response: {str(e)}",
                "confidence": 0.1,
                "extracted_fields": {}
            }
    
    def _validate_extracted_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted data according to schema"""
        cleaned_data = {
            "extraction_success": True,
            "confidence": data.get("confidence", 0.5),
            "extracted_fields": {}
        }
        
        for field_name, field_info in schema["fields"].items():
            if field_name in data:
                value = data[field_name]
                field_type = field_info["type"]
                
                # Type validation and conversion
                try:
                    if field_type == "string" and value is not None:
                        cleaned_data["extracted_fields"][field_name] = str(value).strip()
                    elif field_type == "number" and value is not None:
                        # Try to extract number from string if needed
                        if isinstance(value, str):
                            # Remove currency symbols and commas
                            cleaned_value = re.sub(r'[^\d.-]', '', value)
                            cleaned_data["extracted_fields"][field_name] = float(cleaned_value) if cleaned_value else None
                        else:
                            cleaned_data["extracted_fields"][field_name] = float(value)
                    elif field_type in ["date", "datetime"] and value is not None:
                        # Basic date validation (could be enhanced)
                        cleaned_data["extracted_fields"][field_name] = str(value).strip()
                    elif field_type == "array" and value is not None:
                        if isinstance(value, list):
                            cleaned_data["extracted_fields"][field_name] = value
                        else:
                            cleaned_data["extracted_fields"][field_name] = [value]
                    elif field_type == "object" and value is not None:
                        cleaned_data["extracted_fields"][field_name] = value if isinstance(value, dict) else {}
                    else:
                        cleaned_data["extracted_fields"][field_name] = value
                
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to validate field {field_name}: {e}")
                    cleaned_data["extracted_fields"][field_name] = None
            else:
                cleaned_data["extracted_fields"][field_name] = None
        
        return cleaned_data
    
    def _fallback_extraction(self, content: str, document_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based extraction when LLM fails"""
        logger.info("Using fallback rule-based extraction")
        
        extracted_fields = {}
        
        # Basic pattern matching for common fields
        patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "date": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            "currency": r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
            "number": r'\b\d+(?:,\d{3})*(?:\.\d{2})?\b'
        }
        
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                extracted_fields[f"{pattern_name}_matches"] = matches[:5]  # Limit to first 5 matches
        
        return {
            "extraction_success": True,
            "confidence": 0.3,
            "extracted_fields": extracted_fields,
            "extraction_method": "rule_based_fallback"
        }


async def extraction_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Extraction Agent - Extracts structured data from documents
    
    Responsibilities:
    1. Use document type to determine extraction schema
    2. Extract structured data using LLM
    3. Validate and clean extracted data
    4. Provide confidence scores
    5. Fallback to rule-based extraction if needed
    
    Args:
        state: Current document processing state
    
    Returns:
        Updated state with extraction results
    """
    start_time = time.time()
    agent_name = "extraction"
    
    # Add start entry to history
    state = add_agent_history_entry(state, agent_name, "started")
    state["current_agent"] = agent_name
    
    try:
        logger.info(f"Starting extraction for document: {state['document']['id']}")
        
        # Check if classification was successful
        classification_result = state.get("classification_result")
        if not classification_result or not classification_result["success"]:
            raise ValueError("Cannot extract data: classification failed or incomplete")
        
        # Get document information
        content = state["document"]["content"]
        document_type = state.get("document_type", "other")
        metadata = state["document"]["metadata"]
        
        if not content or not content.strip():
            raise ValueError("No content available for extraction")
        
        # Initialize extractor
        llm_config = state.get("llm_config", {})
        extractor = DataExtractor(llm_config)
        
        # Perform extraction
        extraction_result = await extractor.extract_data(content, document_type, metadata)
        
        # Update extracted data in state
        state["extracted_data"] = extraction_result.get("extracted_fields", {})
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create successful result
        result = AgentResult(
            success=extraction_result.get("extraction_success", False),
            result={
                "extracted_fields": extraction_result.get("extracted_fields", {}),
                "field_count": len(extraction_result.get("extracted_fields", {})),
                "non_null_fields": len([v for v in extraction_result.get("extracted_fields", {}).values() if v is not None]),
                "extraction_method": extraction_result.get("extraction_method", "llm"),
                "document_type": document_type,
                "schema_used": document_type
            },
            error=extraction_result.get("error"),
            confidence_score=extraction_result.get("confidence", 0.5),
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        # Update state
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "completed", result)
        
        logger.info(f"Extraction completed: {result['result']['non_null_fields']} fields extracted "
                   f"(confidence: {result['confidence_score']:.2f})")
        
        return state
    
    except Exception as e:
        # Handle errors
        processing_time = time.time() - start_time
        error_msg = f"Extraction failed: {str(e)}"
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