"""
Classification Agent - Classifies document type using LLM.
Second agent in the document processing pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from workflows.state_schema import DocumentProcessingState, AgentResult, add_agent_history_entry, update_agent_result

logger = logging.getLogger(__name__)


# Document type definitions with characteristics
DOCUMENT_TYPES = {
    "invoice": {
        "description": "Commercial invoice for goods or services",
        "keywords": ["invoice", "bill", "amount due", "payment terms", "tax", "total", "subtotal", "due date", "vendor", "customer", "payment", "billing", "charge", "cost", "price", "fee", "amount", "balance", "receipt", "statement"],
        "patterns": ["invoice number", "due date", "billing address", "line items", "invoice #", "inv #", "bill #", "amount:", "$", "total:", "subtotal:", "tax:", "due:", "from:", "to:", "vendor:", "customer:", "client:", "company:", "corp", "ltd", "llc", "inc"],
        "file_indicators": ["invoice", "bill", "receipt", "statement", "charge"]
    },
    "contract": {
        "description": "Legal agreement between parties",
        "keywords": ["agreement", "contract", "terms", "conditions", "parties", "signature", "effective date"],
        "patterns": ["whereas", "party of the first part", "terms and conditions", "governing law"]
    },
    "resume": {
        "description": "Professional resume or CV",
        "keywords": ["experience", "education", "skills", "employment", "qualifications", "objective"],
        "patterns": ["work experience", "education section", "contact information", "skills section"]
    },
    "financial_statement": {
        "description": "Financial report or statement",
        "keywords": ["balance sheet", "income statement", "cash flow", "assets", "liabilities", "revenue"],
        "patterns": ["financial year", "accounting period", "audited", "unaudited"]
    },
    "legal_document": {
        "description": "Legal document or court filing",
        "keywords": ["court", "plaintiff", "defendant", "jurisdiction", "legal", "statute", "law"],
        "patterns": ["case number", "court filing", "legal citation", "whereas"]
    },
    "medical_record": {
        "description": "Medical document or health record",
        "keywords": ["patient", "diagnosis", "treatment", "medical", "doctor", "hospital", "prescription"],
        "patterns": ["patient name", "date of birth", "medical record number", "diagnosis"]
    },
    "research_paper": {
        "description": "Academic or research paper",
        "keywords": ["abstract", "introduction", "methodology", "results", "conclusion", "references", "citation"],
        "patterns": ["abstract section", "literature review", "bibliography", "peer review"]
    },
    "technical_manual": {
        "description": "Technical documentation or manual",
        "keywords": ["manual", "instructions", "procedure", "technical", "specifications", "installation"],
        "patterns": ["step-by-step", "technical specifications", "troubleshooting", "user guide"]
    },
    "email": {
        "description": "Email correspondence",
        "keywords": ["from", "to", "subject", "sent", "received", "reply", "forward"],
        "patterns": ["email header", "sender", "recipient", "timestamp"]
    },
    "report": {
        "description": "Business or analytical report",
        "keywords": ["report", "analysis", "summary", "findings", "recommendations", "executive summary"],
        "patterns": ["executive summary", "key findings", "methodology", "recommendations"]
    },
    "other": {
        "description": "Document that doesn't fit standard categories",
        "keywords": [],
        "patterns": []
    }
}


class DocumentClassifier:
    """Handles document classification using LLM"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        """Initialize classifier with LLM configuration"""
        self.llm_config = llm_config
        self.llm = self._create_llm()
    
    def _create_llm(self):
        """Create LLM instance based on configuration"""
        provider = self.llm_config.get("provider", "openai")
        model = self.llm_config.get("model", "gpt-4")
        temperature = self.llm_config.get("temperature", 0.1)
        max_tokens = self.llm_config.get("max_tokens", 1000)
        
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
    
    async def classify_document(self, content: str, metadata: Dict[str, Any], invoice_bias: bool = False) -> Dict[str, Any]:
        """
        Classify document using LLM
        
        Args:
            content: Document content
            metadata: Document metadata
        
        Returns:
            Classification result with type, confidence, and reasoning
        """
        try:
            # Create classification prompt
            prompt = self._create_classification_prompt(content, metadata, invoice_bias)
            
            # Get LLM response
            response = await self.llm.ainvoke(prompt)
            
            # Parse response
            result = self._parse_classification_response(response.content)
            
            return result
        
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Fallback to rule-based classification
            return self._fallback_classification(content, metadata, invoice_bias)
    
    def _create_classification_prompt(self, content: str, metadata: Dict[str, Any], invoice_bias: bool = False) -> List:
        """Create classification prompt for LLM"""
        
        # Truncate content if too long
        max_content_length = 3000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "... [truncated]"
        
        # Create document type descriptions
        type_descriptions = []
        for doc_type, info in DOCUMENT_TYPES.items():
            type_descriptions.append(f"- {doc_type}: {info['description']}")
        
        system_message = SystemMessage(content=f"""
You are a document classification expert. Your task is to classify documents into one of the following types:

{chr(10).join(type_descriptions)}

For each document, analyze:
1. Content structure and format
2. Key terminology and language patterns
3. Document purpose and context
4. Metadata clues (filename, file type, etc.)

Respond with a JSON object containing:
- "document_type": the most appropriate type from the list above
- "confidence": confidence score from 0.0 to 1.0
- "reasoning": brief explanation of your classification decision
- "alternative_types": list of other possible types with their confidence scores
- "key_indicators": list of specific content elements that influenced your decision

Be precise and provide clear reasoning for your classification.

{"IMPORTANT: This document shows strong indicators of being an INVOICE based on filename or content analysis. Give extra consideration to classifying it as 'invoice' unless clearly contradicted by the content." if invoice_bias else ""}
""")
        
        human_message = HumanMessage(content=f"""
Please classify this document:

METADATA:
- File type: {metadata.get('file_type', 'unknown')}
- Filename: {metadata.get('original_filename', 'unknown')}
- Content length: {metadata.get('content_length', 0)} characters
- Extraction method: {metadata.get('extraction_method', 'unknown')}

CONTENT:
{content}

Classify this document and provide your analysis in the requested JSON format.
""")
        
        return [system_message, human_message]
    
    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM classification response"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Validate required fields
                required_fields = ["document_type", "confidence", "reasoning"]
                for field in required_fields:
                    if field not in result:
                        raise ValueError(f"Missing required field: {field}")
                
                # Ensure document type is valid
                if result["document_type"] not in DOCUMENT_TYPES:
                    result["document_type"] = "other"
                
                # Ensure confidence is in valid range
                result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
                
                return result
            
            else:
                raise ValueError("No JSON found in response")
        
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                "document_type": "other",
                "confidence": 0.3,
                "reasoning": f"Failed to parse LLM response: {str(e)}",
                "alternative_types": [],
                "key_indicators": []
            }
    
    def _fallback_classification(self, content: str, metadata: Dict[str, Any], invoice_bias: bool = False) -> Dict[str, Any]:
        """Fallback rule-based classification when LLM fails"""
        logger.info("Using fallback rule-based classification")
        
        content_lower = content.lower()
        scores = {}
        
        # Score each document type based on keyword matching
        for doc_type, info in DOCUMENT_TYPES.items():
            if doc_type == "other":
                continue
            
            score = 0
            matched_keywords = []
            matched_patterns = []
            
            # Check keywords
            for keyword in info["keywords"]:
                if keyword.lower() in content_lower:
                    score += 1
                    matched_keywords.append(keyword)
            
            # Check patterns
            for pattern in info["patterns"]:
                if pattern.lower() in content_lower:
                    score += 2  # Patterns are weighted higher
                    matched_patterns.append(pattern)
            
            if score > 0:
                scores[doc_type] = {
                    "score": score,
                    "keywords": matched_keywords,
                    "patterns": matched_patterns
                }
        
        # Determine best match
        # Apply invoice bias if detected
        if invoice_bias and "invoice" in scores:
            scores["invoice"]["score"] += 5  # Boost invoice score significantly
            logger.info(f"Applied invoice bias - boosted invoice score to {scores['invoice']['score']}")
        
        if scores:
            best_type = max(scores.keys(), key=lambda k: scores[k]["score"])
            best_score = scores[best_type]["score"]
            
            # Calculate confidence based on score
            max_possible_score = len(DOCUMENT_TYPES[best_type]["keywords"]) + (len(DOCUMENT_TYPES[best_type]["patterns"]) * 2)
            confidence = min(0.9, (best_score / max(max_possible_score, 1)) * 0.8 + 0.2)
            
            # Boost confidence if invoice bias was applied and invoice was selected
            if invoice_bias and best_type == "invoice":
                confidence = min(0.95, confidence + 0.2)
            
            return {
                "document_type": best_type,
                "confidence": confidence,
                "reasoning": f"Rule-based classification based on {best_score} matching indicators",
                "alternative_types": [{"type": t, "confidence": scores[t]["score"] / max(best_score, 1) * confidence} 
                                    for t in scores.keys() if t != best_type],
                "key_indicators": scores[best_type]["keywords"] + scores[best_type]["patterns"]
            }
        else:
            return {
                "document_type": "other",
                "confidence": 0.2,
                "reasoning": "No clear classification indicators found",
                "alternative_types": [],
                "key_indicators": []
            }


async def classification_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Classification Agent - Classifies document type using LLM
    
    Responsibilities:
    1. Analyze document content and metadata
    2. Use LLM to classify document type
    3. Provide confidence scores and reasoning
    4. Fallback to rule-based classification if needed
    5. Update state with classification results
    
    Args:
        state: Current document processing state
    
    Returns:
        Updated state with classification results
    """
    start_time = time.time()
    agent_name = "classification"
    
    # Add start entry to history
    state = add_agent_history_entry(state, agent_name, "started")
    state["current_agent"] = agent_name
    
    try:
        logger.info(f"Starting classification for document: {state['document']['id']}")
        
        # Check if ingestion was successful
        ingestion_result = state.get("ingestion_result")
        if not ingestion_result or not ingestion_result["success"]:
            raise ValueError("Cannot classify document: ingestion failed or incomplete")
        
        # Pre-classification check for obvious invoice indicators
        content = state["document"]["content"]
        filename = state["document"].get("filename", "")
        
        # Check filename for invoice indicators
        filename_lower = filename.lower()
        invoice_filename_indicators = ["invoice", "bill", "receipt", "statement", "inv"]
        filename_suggests_invoice = any(indicator in filename_lower for indicator in invoice_filename_indicators)
        
        # Check content for strong invoice indicators
        content_lower = content.lower()
        strong_invoice_indicators = [
            "invoice #", "invoice number", "inv #", "bill #", 
            "amount due", "total due", "payment due", "balance due",
            "invoice date", "due date", "billing date",
            "vendor:", "customer:", "bill to:", "invoice to:",
            "subtotal", "tax amount", "total amount", "$", "amount:", "total:", "cost:", "price:", "fee:"
        ]
        content_has_strong_indicators = sum(1 for indicator in strong_invoice_indicators if indicator in content_lower)
        
        # If filename suggests invoice OR content has multiple strong indicators, bias toward invoice
        invoice_bias = filename_suggests_invoice or content_has_strong_indicators >= 2
        
        logger.info(f"Invoice detection - filename_suggests: {filename_suggests_invoice}, content_indicators: {content_has_strong_indicators}, bias: {invoice_bias}")
        
        # Get document content and metadata
        content = state["document"]["content"]
        metadata = state["document"]["metadata"]
        
        if not content or not content.strip():
            raise ValueError("No content available for classification")
        
        # Initialize classifier
        llm_config = state.get("llm_config", {})
        classifier = DocumentClassifier(llm_config)
        
        # Perform classification
        classification_result = await classifier.classify_document(content, metadata, invoice_bias)
        
        # Update document type in state
        state["document_type"] = classification_result["document_type"]
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create successful result
        result = AgentResult(
            success=True,
            result={
                "document_type": classification_result["document_type"],
                "confidence": classification_result["confidence"],
                "reasoning": classification_result["reasoning"],
                "alternative_types": classification_result.get("alternative_types", []),
                "key_indicators": classification_result.get("key_indicators", []),
                "classification_method": "llm" if "Failed to parse LLM response" not in classification_result["reasoning"] else "rule_based"
            },
            error=None,
            confidence_score=classification_result["confidence"],
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        # Update state
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "completed", result)
        
        logger.info(f"Classification completed: {classification_result['document_type']} "
                   f"(confidence: {classification_result['confidence']:.2f})")
        
        return state
    
    except Exception as e:
        # Handle errors
        processing_time = time.time() - start_time
        error_msg = f"Classification failed: {str(e)}"
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