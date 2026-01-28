"""
WebSocket Manager for real-time communication.
Handles WebSocket connections and broadcasting for document processing updates.
"""

import asyncio
import logging
import json
from typing import Dict, List, Set
from datetime import datetime

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates
    
    Provides functionality to:
    1. Connect/disconnect WebSocket clients
    2. Broadcast messages to specific documents
    3. Broadcast messages to all connected clients
    4. Handle connection cleanup
    """
    
    def __init__(self):
        """Initialize WebSocket manager"""
        # Dictionary mapping document_id to list of WebSocket connections
        self.document_connections: Dict[str, List[WebSocket]] = {}
        
        # Set of all active connections for cleanup
        self.active_connections: Set[WebSocket] = set()
        
        logger.info("WebSocket manager initialized")
    
    async def connect(self, websocket: WebSocket, document_id: str):
        """
        Accept a new WebSocket connection for a document
        
        Args:
            websocket: WebSocket connection
            document_id: Document identifier
        """
        try:
            await websocket.accept()
            
            # Add to document-specific connections
            if document_id not in self.document_connections:
                self.document_connections[document_id] = []
            
            self.document_connections[document_id].append(websocket)
            self.active_connections.add(websocket)
            
            logger.info(f"WebSocket connected for document: {document_id}")
            
            # Send welcome message
            await websocket.send_json({
                "type": "connection_established",
                "document_id": document_id,
                "timestamp": datetime.now().isoformat(),
                "message": f"Connected to document {document_id} updates"
            })
        
        except Exception as e:
            logger.error(f"Failed to connect WebSocket for document {document_id}: {e}")
            await self._cleanup_connection(websocket, document_id)
    
    def disconnect(self, websocket: WebSocket, document_id: str):
        """
        Disconnect a WebSocket connection
        
        Args:
            websocket: WebSocket connection
            document_id: Document identifier
        """
        try:
            # Remove from document connections
            if document_id in self.document_connections:
                if websocket in self.document_connections[document_id]:
                    self.document_connections[document_id].remove(websocket)
                
                # Clean up empty document connection lists
                if not self.document_connections[document_id]:
                    del self.document_connections[document_id]
            
            # Remove from active connections
            self.active_connections.discard(websocket)
            
            logger.info(f"WebSocket disconnected for document: {document_id}")
        
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect for document {document_id}: {e}")
    
    async def broadcast_to_document(self, document_id: str, message: Dict):
        """
        Broadcast a message to all connections for a specific document
        
        Args:
            document_id: Document identifier
            message: Message to broadcast
        """
        if document_id not in self.document_connections:
            logger.debug(f"No WebSocket connections for document: {document_id}")
            return
        
        connections = self.document_connections[document_id].copy()
        disconnected_connections = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.debug(f"Sent message to WebSocket for document {document_id}: {message.get('type', 'unknown')}")
            
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket for document {document_id}: {e}")
                disconnected_connections.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            self.disconnect(websocket, document_id)
    
    async def broadcast_to_all(self, message: Dict):
        """
        Broadcast a message to all active connections
        
        Args:
            message: Message to broadcast
        """
        if not self.active_connections:
            logger.debug("No active WebSocket connections for broadcast")
            return
        
        connections = self.active_connections.copy()
        disconnected_connections = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.debug(f"Sent broadcast message: {message.get('type', 'unknown')}")
            
            except Exception as e:
                logger.warning(f"Failed to send broadcast message: {e}")
                disconnected_connections.append(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            # Find document_id for cleanup
            document_id = None
            for doc_id, doc_connections in self.document_connections.items():
                if websocket in doc_connections:
                    document_id = doc_id
                    break
            
            if document_id:
                self.disconnect(websocket, document_id)
    
    async def send_processing_update(self, document_id: str, agent_name: str, 
                                   status: str, result: Dict = None):
        """
        Send a processing update for a specific agent
        
        Args:
            document_id: Document identifier
            agent_name: Name of the agent
            status: Processing status (started, completed, failed)
            result: Agent result data (optional)
        """
        message = {
            "type": "agent_update",
            "document_id": document_id,
            "agent_name": agent_name,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        if result:
            message["result"] = {
                "success": result.get("success", False),
                "confidence_score": result.get("confidence_score"),
                "processing_time": result.get("processing_time"),
                "error": result.get("error")
            }
        
        await self.broadcast_to_document(document_id, message)
    
    async def send_workflow_status(self, document_id: str, status_info: Dict):
        """
        Send workflow status update
        
        Args:
            document_id: Document identifier
            status_info: Workflow status information
        """
        message = {
            "type": "workflow_status",
            "document_id": document_id,
            "status_info": status_info,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast_to_document(document_id, message)
    
    async def send_human_review_required(self, document_id: str, review_request: Dict):
        """
        Send notification that human review is required
        
        Args:
            document_id: Document identifier
            review_request: Human review request details
        """
        message = {
            "type": "human_review_required",
            "document_id": document_id,
            "review_request": review_request,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast_to_document(document_id, message)
    
    async def send_error_notification(self, document_id: str, error: str, 
                                    agent_name: str = None):
        """
        Send error notification
        
        Args:
            document_id: Document identifier
            error: Error message
            agent_name: Name of agent that failed (optional)
        """
        message = {
            "type": "error_notification",
            "document_id": document_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        if agent_name:
            message["agent_name"] = agent_name
        
        await self.broadcast_to_document(document_id, message)
    
    async def send_completion_notification(self, document_id: str, final_status: str,
                                         processing_time: float = None):
        """
        Send workflow completion notification
        
        Args:
            document_id: Document identifier
            final_status: Final workflow status
            processing_time: Total processing time (optional)
        """
        message = {
            "type": "workflow_completed",
            "document_id": document_id,
            "final_status": final_status,
            "timestamp": datetime.now().isoformat()
        }
        
        if processing_time:
            message["processing_time"] = processing_time
        
        await self.broadcast_to_document(document_id, message)
    
    async def _cleanup_connection(self, websocket: WebSocket, document_id: str):
        """
        Clean up a failed connection
        
        Args:
            websocket: WebSocket connection
            document_id: Document identifier
        """
        try:
            self.disconnect(websocket, document_id)
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
    
    def get_connection_stats(self) -> Dict[str, int]:
        """
        Get connection statistics
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "total_active_connections": len(self.active_connections),
            "documents_with_connections": len(self.document_connections),
            "connections_per_document": {
                doc_id: len(connections) 
                for doc_id, connections in self.document_connections.items()
            }
        }
    
    async def ping_all_connections(self):
        """
        Send ping to all connections to check connectivity
        """
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast_to_all(ping_message)
    
    async def cleanup_stale_connections(self):
        """
        Clean up stale connections that are no longer responsive
        """
        logger.info("Starting cleanup of stale WebSocket connections")
        
        stale_connections = []
        
        for websocket in self.active_connections.copy():
            try:
                # Try to send a ping
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception:
                # Connection is stale
                stale_connections.append(websocket)
        
        # Clean up stale connections
        for websocket in stale_connections:
            # Find document_id for cleanup
            document_id = None
            for doc_id, doc_connections in self.document_connections.items():
                if websocket in doc_connections:
                    document_id = doc_id
                    break
            
            if document_id:
                self.disconnect(websocket, document_id)
        
        logger.info(f"Cleaned up {len(stale_connections)} stale WebSocket connections")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Periodic cleanup task
async def periodic_cleanup():
    """Periodic task to clean up stale connections"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            await websocket_manager.cleanup_stale_connections()
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


# Periodic cleanup task will be started by the FastAPI app
# asyncio.create_task(periodic_cleanup())  # Commented out to avoid import issues