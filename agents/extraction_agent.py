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


# Dynamic extraction - NO hardcoded schemas
# The agent intelligently discovers and extracts fields based on document content


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
            # Dynamic extraction - let AI discover the fields based on document type
            prompt = self._create_dynamic_extraction_prompt(content, document_type, metadata)
            
            # Get LLM response
            response = await self.llm.ainvoke(prompt)
            
            # Parse dynamic response
            result = self._parse_dynamic_extraction_response(response.content, document_type)
            
            return result
        
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Fallback to basic extraction
            return self._fallback_extraction(content, document_type, metadata)
    
    def _create_dynamic_extraction_prompt(self, content: str, document_type: str, metadata: Dict[str, Any]) -> List:
        """Create dynamic extraction prompt - AI discovers fields intelligently"""
        
        # Truncate content if too long
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "... [truncated]"
        
        system_message = SystemMessage(content=f"""
You are an intelligent document processing agent in a horizontal, self-learning platform. Your role is to DYNAMICALLY analyze ANY document type and extract ALL relevant structured information.

DYNAMIC EXTRACTION PRINCIPLES:
1. Intelligently identify what TYPE of document this is
2. Discover ALL key fields present in the document (don't rely on predefined schemas)
3. Extract field names and values as they appear in the document
4. Identify relationships between entities
5. Recognize patterns (dates, amounts, names, IDs, etc.)
6. Understand document purpose and extract accordingly

OUTPUT FORMAT - Return a JSON with this structure:
{{
  "document_analysis": {{
    "identified_type": "the specific document type you identified",
    "confidence": 0.0-1.0,
    "primary_purpose": "what this document is for"
  }},
  "extracted_fields": {{
    // ALL fields you discovered with their values
    // Use the field names as they appear in the document
    // Example: "invoice_number", "patient_name", "passport_number", etc.
  }},
  "entities": {{
    "people": [],
    "organizations": [],
    "locations": []
  }},
  "temporal_data": {{
    "dates": [],
    "deadlines": [],
    "periods": []
  }},
  "financial_data": {{
    "amounts": [],
    "currencies": [],
    "transactions": []
  }},
  "key_insights": {{
    "summary": "2-3 sentence overview",
    "key_points": ["critical info point 1", "point 2", ...],
    "action_items": ["required actions if any"],
    "status": "document status if applicable"
  }},
  "metadata": {{
    // Any additional structured information you extracted
  }}
}}

EXTRACTION GUIDELINES:
- Be thorough - extract EVERYTHING of value
- Use actual field names from the document (e.g., "Invoice Number", "Passport No", "Patient ID")
- Identify ALL entities (people, companies, locations)
- Extract ALL dates and understand their meaning
- Extract ALL monetary values and quantities
- Identify document status and any actions needed
- Generate an intelligent summary
- Don't force a schema - adapt to what the document contains
- If a field type is unclear, extract it anyway and let validation handle it

INTELLIGENCE REQUIREMENTS:
- Understand context (e.g., "Net 30" means payment terms)
- Recognize synonyms (e.g., "vendor", "supplier", "seller" all mean the same)
- Extract implicit information (e.g., if there's a "Bill To" and "Ship To", those are entities)
- Identify hierarchies (e.g., line items belong to an invoice)
- Recognize document-specific patterns (invoices have totals, passports have expiry dates, etc.)

Remember: You are NOT limited to predefined fields. Discover and extract ALL relevant information.
""")
        
        human_message = HumanMessage(content=f"""
Analyze and extract ALL structured information from this document:

DOCUMENT CONTEXT:
- Classified as: {document_type}
- File type: {metadata.get('file_type', 'unknown')}
- Content length: {metadata.get('content_length', 0)} characters

DOCUMENT CONTENT:
{content}

Perform dynamic extraction - discover all fields, entities, dates, amounts, and relationships. Return complete structured data as JSON.
""")
        
        return [system_message, human_message]
    
    def _parse_dynamic_extraction_response(self, response: str, document_type: str) -> Dict[str, Any]:
        """Parse dynamic extraction response without enforcing a fixed schema"""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Return the dynamically extracted data
                return {
                    "extraction_success": True,
                    "document_type": document_type,
                    "identified_type": result.get("document_analysis", {}).get("identified_type", document_type),
                    "confidence": result.get("document_analysis", {}).get("confidence", 0.7),
                    "extracted_fields": result.get("extracted_fields", {}),
                    "entities": result.get("entities", {}),
                    "temporal_data": result.get("temporal_data", {}),
                    "financial_data": result.get("financial_data", {}),
                    "key_insights": result.get("key_insights", {}),
                    "metadata": result.get("metadata", {}),
                    "raw_extraction": result
                }
            else:
                raise ValueError("No JSON found in response")
        
        except Exception as e:
            logger.error(f"Failed to parse dynamic extraction response: {e}")
            return {
                "extraction_success": False,
                "error": f"Failed to parse LLM response: {str(e)}",
                "confidence": 0.1,
                "extracted_fields": {}
            }
    
    def _parse_extraction_response_legacy(self, response: str, schema: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # Perform dynamic extraction
        extraction_result = await extractor.extract_data(content, document_type, metadata)
        
        # Store complete dynamic extraction result
        # This preserves all discovered fields, entities, temporal data, insights, etc.
        state["extracted_data"] = {
            **extraction_result.get("extracted_fields", {}),  # All discovered fields
            "_insights": extraction_result.get("key_insights", {}),  # Key insights (summary, key_points, actions)
            "_entities": extraction_result.get("entities", {}),  # Discovered entities
            "_temporal": extraction_result.get("temporal_data", {}),  # All dates and temporal info
            "_financial": extraction_result.get("financial_data", {}),  # All amounts and financial data
            "_metadata": extraction_result.get("metadata", {}),  # Additional metadata
            "_analysis": {
                "identified_type": extraction_result.get("identified_type", document_type),
                "classified_as": document_type,
                "extraction_method": "dynamic_ai"
            }
        }
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create successful result
        result = AgentResult(
            success=extraction_result.get("extraction_success", False),
            result={
                "extracted_fields_count": len(extraction_result.get("extracted_fields", {})),
                "entities_found": extraction_result.get("entities", {}),
                "temporal_data": extraction_result.get("temporal_data", {}),
                "financial_data": extraction_result.get("financial_data", {}),
                "key_insights": extraction_result.get("key_insights", {}),
                "extraction_method": "dynamic",
                "document_type": document_type,
                "identified_as": extraction_result.get("identified_type", document_type)
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