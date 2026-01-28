# Document Processing Platform - Lovable Integration Guide

## Overview

This document provides integration instructions for connecting your Lovable frontend to the Document Processing Platform backend.

## Backend Configuration

The backend is configured to accept requests from Lovable domains with proper CORS settings:

- Local development: `http://localhost:3000`
- Lovable preview: `https://*.lovable.dev`
- Lovable production: `https://*.lovableproject.com`

## API Endpoints

### Base URL
- Development: `http://localhost:8000`
- Production: Update with your deployed URL

### Core Endpoints

#### 1. Health Check
```
GET /health
```
Returns server status and timestamp.

#### 2. Process Document (File Upload)
```
POST /process-document
Content-Type: multipart/form-data

Body:
- file: File (pdf, docx, txt, jpg, jpeg, png)
```

Response:
```json
{
  "success": true,
  "document_id": "uuid",
  "workflow_id": "workflow_uuid",
  "thread_id": "thread_uuid_timestamp",
  "message": "Document uploaded successfully. Processing started.",
  "status": "processing",
  "requires_human_review": false
}
```

#### 3. Process Text (Direct Text)
```
POST /process-text
Content-Type: application/json

Body:
{
  "text_content": "Your text content here",
  "document_type": "txt"
}
```

#### 4. Get Processing Status
```
GET /status/{thread_id}
```

Response:
```json
{
  "workflow_id": "string",
  "document_id": "string", 
  "current_status": "processing|completed|failed|human_review_required",
  "current_agent": "agent_name",
  "next_agent": "next_agent_name",
  "progress": {},
  "timing": {},
  "human_interaction": {},
  "quality_metrics": {},
  "is_complete": false,
  "can_continue": true
}
```

#### 5. Get Processing Results
```
GET /results/{thread_id}
```

Response:
```json
{
  "success": true,
  "document_id": "string",
  "workflow_id": "string", 
  "status": "completed",
  "extracted_data": {},
  "validated_data": {},
  "business_rules_applied": [],
  "anomalies_detected": [],
  "human_review_required": false,
  "processing_time": 0.0,
  "confidence_scores": {}
}
```

#### 6. Submit Human Review
```
POST /human-review/{thread_id}/submit
Content-Type: application/json

Body:
{
  "decision": "approve|reject|modify|escalate",
  "feedback": "Review feedback text",
  "reviewer": "reviewer_id",
  "modifications": {} // Optional
}
```

#### 7. Get Human Review Context
```
GET /human-review/{thread_id}/context
```

### WebSocket Connection

For real-time updates:
```
ws://localhost:8000/workflow/{document_id}/stream
```

Message types:
- `processing_started`
- `processing_completed`
- `processing_failed`
- `human_review_required`
- `processing_error`

## Frontend Integration Examples

### React/TypeScript Example

```typescript
// API client setup
const API_BASE_URL = 'http://localhost:8000';

// File upload
const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/process-document`, {
    method: 'POST',
    body: formData,
  });
  
  return response.json();
};

// Text processing
const processText = async (text: string, documentType: string = 'txt') => {
  const response = await fetch(`${API_BASE_URL}/process-text`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text_content: text,
      document_type: documentType,
    }),
  });
  
  return response.json();
};

// Get status
const getStatus = async (threadId: string) => {
  const response = await fetch(`${API_BASE_URL}/status/${threadId}`);
  return response.json();
};

// WebSocket connection
const connectWebSocket = (documentId: string) => {
  const ws = new WebSocket(`ws://localhost:8000/workflow/${documentId}/stream`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Workflow update:', data);
    // Handle real-time updates
  };
  
  return ws;
};
```

### Vue.js Example

```javascript
// Composable for document processing
import { ref, reactive } from 'vue'

export function useDocumentProcessing() {
  const isProcessing = ref(false)
  const results = reactive({})
  
  const processDocument = async (file) => {
    isProcessing.value = true
    
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      const response = await fetch('http://localhost:8000/process-document', {
        method: 'POST',
        body: formData
      })
      
      const result = await response.json()
      
      // Poll for status updates
      pollStatus(result.thread_id)
      
      return result
    } catch (error) {
      console.error('Processing failed:', error)
    } finally {
      isProcessing.value = false
    }
  }
  
  const pollStatus = async (threadId) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/status/${threadId}`)
        const status = await response.json()
        
        if (status.is_complete) {
          clearInterval(interval)
          // Get final results
          const resultsResponse = await fetch(`http://localhost:8000/results/${threadId}`)
          Object.assign(results, await resultsResponse.json())
        }
      } catch (error) {
        console.error('Status check failed:', error)
        clearInterval(interval)
      }
    }, 2000)
  }
  
  return {
    isProcessing,
    results,
    processDocument
  }
}
```

## Error Handling

Common error responses:
- `400`: Bad Request (invalid file type, missing content)
- `404`: Not Found (document/thread not found)
- `500`: Internal Server Error

Always check the `success` field in responses and handle errors appropriately.

## Security Considerations

1. **API Keys**: The backend requires OpenAI API keys. Ensure these are set as environment variables.
2. **File Validation**: Only supported file types are accepted.
3. **CORS**: Configured for Lovable domains, but verify in production.

## Deployment Notes

1. **Environment Variables**: Set `OPENAI_API_KEY` in your deployment environment.
2. **File Storage**: Ensure the `uploads/` directory is writable.
3. **Database**: Consider adding persistent storage for production use.
4. **Scaling**: The current implementation uses in-memory state. Consider Redis for production.

## Testing the Integration

1. Start the backend server:
```bash
cd /path/to/LyzrAgent
source venv/bin/activate
export OPENAI_API_KEY="your-key-here"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Test endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Process text
curl -X POST "http://localhost:8000/process-text" \
  -H "Content-Type: application/json" \
  -d '{"text_content": "Test document content", "document_type": "txt"}'
```

3. Access API documentation: `http://localhost:8000/docs`

## Support

For issues or questions about the integration, refer to the API documentation at `/docs` or check the server logs for detailed error information.