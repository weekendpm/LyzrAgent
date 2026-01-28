# 🔗 Lovable Integration Guide

## Overview
This FastAPI backend is ready to integrate with Lovable's frontend development platform. The API provides document processing capabilities with 9 AI agents.

## 🚀 Quick Start for Lovable

### 1. Backend Setup
```bash
# Start your FastAPI server
cd /Users/rudranshtiwri/Code/LyzrAgent
source venv/bin/activate
export OPENAI_API_KEY="your-api-key-here"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. API Endpoints for Lovable

#### Core Endpoints:
- `GET /` - API information and available endpoints
- `GET /health` - Health check
- `POST /upload-and-process` - Upload file and start processing
- `GET /simple-status/{document_id}?thread_id={thread_id}` - Simplified status for UI
- `POST /process-text` - Process text directly
- `WebSocket /workflow/{document_id}/stream` - Real-time updates

#### Example Usage in Lovable:

```javascript
// Upload and process a document
const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/upload-and-process', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
};

// Check processing status
const checkStatus = async (documentId, threadId) => {
  const response = await fetch(
    `http://localhost:8000/simple-status/${documentId}?thread_id=${threadId}`
  );
  return await response.json();
};

// WebSocket for real-time updates
const connectWebSocket = (documentId) => {
  const ws = new WebSocket(`ws://localhost:8000/workflow/${documentId}/stream`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Processing update:', data);
  };
  
  return ws;
};
```

## 🎨 Frontend Integration Examples

### React Component Example:
```jsx
import React, { useState, useEffect } from 'react';

const DocumentProcessor = () => {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [processing, setProcessing] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    
    setProcessing(true);
    const result = await uploadDocument(file);
    
    if (result.success) {
      // Start polling for status
      pollStatus(result.document_id, result.thread_id);
    }
  };

  const pollStatus = async (documentId, threadId) => {
    const interval = setInterval(async () => {
      const status = await checkStatus(documentId, threadId);
      setStatus(status);
      
      if (status.is_complete || status.status === 'error') {
        clearInterval(interval);
        setProcessing(false);
      }
    }, 2000);
  };

  return (
    <div className="document-processor">
      <input 
        type="file" 
        onChange={(e) => setFile(e.target.files[0])}
        accept=".pdf,.docx,.txt,.jpg,.png"
      />
      <button onClick={handleUpload} disabled={!file || processing}>
        {processing ? 'Processing...' : 'Upload & Process'}
      </button>
      
      {status && (
        <div className="status">
          <h3>Processing Status</h3>
          <p>Status: {status.status}</p>
          <p>Progress: {status.progress_percentage}%</p>
          <p>Current Step: {status.current_step}</p>
          {status.requires_human_review && (
            <p>⚠️ Human review required</p>
          )}
        </div>
      )}
    </div>
  );
};
```

## 🔧 Configuration

### Environment Variables:
```env
OPENAI_API_KEY=sk-your-openai-key
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4
```

### CORS Configuration:
The API is configured to work with:
- `http://localhost:3000` (local development)
- `https://*.lovable.dev` (Lovable preview)
- `https://*.lovableproject.com` (Lovable production)

## 📊 Response Formats

### Simple Status Response:
```json
{
  "document_id": "uuid",
  "status": "processing|completed|error",
  "progress_percentage": 75.0,
  "current_step": "extraction_agent",
  "is_complete": false,
  "requires_human_review": true,
  "error": null
}
```

### Upload Response:
```json
{
  "success": true,
  "document_id": "uuid",
  "thread_id": "thread_uuid_timestamp",
  "filename": "document.pdf",
  "status": "processing",
  "message": "Document uploaded and processing started"
}
```

## 🔄 Real-time Updates

WebSocket messages include:
- `processing_started` - Processing began
- `agent_completed` - Individual agent finished
- `processing_completed` - All processing done
- `processing_error` - Error occurred
- `human_review_required` - Manual review needed

## 🚀 Deployment

For production deployment with Lovable:

1. Update CORS origins to include your Lovable production URLs
2. Set environment variables in your deployment platform
3. Use the health check endpoint (`/health`) for monitoring
4. Consider rate limiting and authentication for production use

## 📝 API Documentation

Once your server is running, visit:
- `http://localhost:8000/docs` - Interactive API documentation
- `http://localhost:8000/redoc` - Alternative documentation format

## 🛠️ Troubleshooting

1. **CORS Issues**: Check that your Lovable URL is in the allowed origins
2. **API Key Issues**: Ensure `OPENAI_API_KEY` is set correctly
3. **WebSocket Issues**: Make sure your frontend handles WebSocket reconnection
4. **File Upload Issues**: Check file size limits and supported formats

## 📞 Support

For issues with the backend integration, check:
1. Server logs for detailed error messages
2. API documentation at `/docs`
3. Health check at `/health`