"""
Ingestion Agent - Handles file validation, processing, and OCR.
First agent in the document processing pipeline.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
import aiofiles
import os
from pathlib import Path

# File processing imports
import PyPDF2
from docx import Document
# OCR imports - disabled for Railway deployment
# from PIL import Image
# import pytesseract

from workflows.state_schema import DocumentProcessingState, AgentResult, add_agent_history_entry, update_agent_result

logger = logging.getLogger(__name__)


class FileProcessor:
    """Handles different file type processing"""
    
    @staticmethod
    async def process_pdf(file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
    
    @staticmethod
    async def process_docx(file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error processing DOCX: {e}")
            raise
    
    @staticmethod
    async def process_txt(file_path: str) -> str:
        """Read text file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
            return content.strip()
        except Exception as e:
            logger.error(f"Error processing TXT: {e}")
            raise
    
    @staticmethod
    async def process_image_ocr(file_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"Error processing image with OCR: {e}")
            raise


async def validate_file(file_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate file before processing
    
    Args:
        file_path: Path to the file
        config: Processing configuration
    
    Returns:
        Validation result with file metadata
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        file_extension = Path(file_path).suffix.lower().lstrip('.')
        
        # Check file size
        max_size = config.get('max_file_size', 50 * 1024 * 1024)  # 50MB default
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")
        
        # Check file type
        supported_types = config.get('supported_file_types', ['pdf', 'docx', 'txt', 'jpg', 'png', 'jpeg'])
        if file_extension not in supported_types:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        return {
            "valid": True,
            "file_size": file_size,
            "file_type": file_extension,
            "file_name": Path(file_path).name,
            "modified_time": datetime.fromtimestamp(file_stat.st_mtime)
        }
    
    except Exception as e:
        logger.error(f"File validation failed: {e}")
        return {
            "valid": False,
            "error": str(e)
        }


async def extract_content(file_path: str, file_type: str, enable_ocr: bool = True) -> str:
    """
    Extract content from file based on type
    
    Args:
        file_path: Path to the file
        file_type: Type of file (pdf, docx, txt, jpg, png)
        enable_ocr: Whether to enable OCR for images
    
    Returns:
        Extracted text content
    """
    processor = FileProcessor()
    
    try:
        if file_type == 'pdf':
            return await processor.process_pdf(file_path)
        elif file_type == 'docx':
            return await processor.process_docx(file_path)
        elif file_type == 'txt':
            return await processor.process_txt(file_path)
        elif file_type in ['jpg', 'jpeg', 'png'] and enable_ocr:
            return await processor.process_image_ocr(file_path)
        else:
            raise ValueError(f"Unsupported file type for content extraction: {file_type}")
    
    except Exception as e:
        logger.error(f"Content extraction failed: {e}")
        raise


async def ingestion_agent(state: DocumentProcessingState) -> DocumentProcessingState:
    """
    Ingestion Agent - First agent in the pipeline
    
    Responsibilities:
    1. Validate file and check constraints
    2. Extract content from various file formats
    3. Perform OCR if needed
    4. Update document metadata
    5. Prepare content for downstream agents
    
    Args:
        state: Current document processing state
    
    Returns:
        Updated state with ingestion results
    """
    start_time = time.time()
    agent_name = "ingestion"
    
    # Add start entry to history
    state = add_agent_history_entry(state, agent_name, "started")
    state["current_agent"] = agent_name
    state["status"] = "processing"
    
    try:
        logger.info(f"Starting ingestion for document: {state['document']['id']}")
        
        # Get configuration
        config = state.get("processing_config", {})
        enable_ocr = config.get("enable_ocr", True)
        
        # Check if we have file path or direct content
        document = state["document"]
        
        if document.get("file_path"):
            # Process file from path
            file_path = document["file_path"]
            
            # Validate file
            validation_result = await validate_file(file_path, config)
            if not validation_result["valid"]:
                raise ValueError(f"File validation failed: {validation_result['error']}")
            
            # Extract content
            content = await extract_content(
                file_path, 
                validation_result["file_type"], 
                enable_ocr
            )
            
            # Update document with extracted content and metadata
            state["document"]["content"] = content
            state["document"]["file_size"] = validation_result["file_size"]
            state["document"]["file_type"] = validation_result["file_type"]
            state["document"]["metadata"].update({
                "original_filename": validation_result["file_name"],
                "file_modified_time": validation_result["modified_time"].isoformat(),
                "content_length": len(content),
                "extraction_method": "ocr" if validation_result["file_type"] in ['jpg', 'jpeg', 'png'] else "native"
            })
            
        else:
            # Content provided directly
            content = document["content"]
            if not content or not content.strip():
                raise ValueError("No content provided for processing")
            
            # Update metadata
            state["document"]["metadata"].update({
                "content_length": len(content),
                "extraction_method": "direct"
            })
        
        # Validate content quality
        content_stats = analyze_content_quality(content)
        
        # Calculate confidence score based on content quality
        confidence_score = calculate_ingestion_confidence(content_stats, state["document"]["file_type"])
        
        # Create successful result
        processing_time = time.time() - start_time
        result = AgentResult(
            success=True,
            result={
                "content_extracted": True,
                "content_length": len(content),
                "content_stats": content_stats,
                "file_metadata": state["document"]["metadata"],
                "extraction_method": state["document"]["metadata"]["extraction_method"]
            },
            error=None,
            confidence_score=confidence_score,
            processing_time=processing_time,
            timestamp=datetime.now()
        )
        
        # Update state
        state = update_agent_result(state, agent_name, result)
        state = add_agent_history_entry(state, agent_name, "completed", result)
        
        logger.info(f"Ingestion completed successfully for document: {state['document']['id']}")
        
        return state
    
    except Exception as e:
        # Handle errors
        processing_time = time.time() - start_time
        error_msg = f"Ingestion failed: {str(e)}"
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
        state["status"] = "failed"
        
        return state


def analyze_content_quality(content: str) -> Dict[str, Any]:
    """
    Analyze the quality of extracted content
    
    Args:
        content: Extracted text content
    
    Returns:
        Content quality statistics
    """
    if not content:
        return {
            "word_count": 0,
            "char_count": 0,
            "line_count": 0,
            "has_meaningful_content": False,
            "estimated_language": "unknown"
        }
    
    lines = content.split('\n')
    words = content.split()
    
    # Basic statistics
    stats = {
        "word_count": len(words),
        "char_count": len(content),
        "line_count": len(lines),
        "non_empty_lines": len([line for line in lines if line.strip()]),
        "avg_words_per_line": len(words) / max(len(lines), 1),
        "has_meaningful_content": len(words) > 10,  # At least 10 words
    }
    
    # Simple language detection (basic heuristic)
    alpha_chars = sum(1 for c in content if c.isalpha())
    stats["alpha_ratio"] = alpha_chars / max(len(content), 1)
    
    # Estimate if content looks like meaningful text
    if stats["word_count"] > 10 and stats["alpha_ratio"] > 0.5:
        stats["quality_score"] = min(1.0, (stats["word_count"] / 100) * stats["alpha_ratio"])
    else:
        stats["quality_score"] = 0.1
    
    return stats


def calculate_ingestion_confidence(content_stats: Dict[str, Any], file_type: str) -> float:
    """
    Calculate confidence score for ingestion based on content quality
    
    Args:
        content_stats: Content quality statistics
        file_type: Type of source file
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    base_confidence = 0.5
    
    # Adjust based on content quality
    quality_score = content_stats.get("quality_score", 0.0)
    base_confidence += quality_score * 0.3
    
    # Adjust based on file type reliability
    file_type_confidence = {
        "txt": 0.95,
        "docx": 0.90,
        "pdf": 0.85,
        "jpg": 0.70,
        "jpeg": 0.70,
        "png": 0.75
    }
    
    type_confidence = file_type_confidence.get(file_type, 0.5)
    final_confidence = (base_confidence + type_confidence) / 2
    
    # Ensure meaningful content exists
    if not content_stats.get("has_meaningful_content", False):
        final_confidence *= 0.3
    
    return min(1.0, max(0.1, final_confidence))