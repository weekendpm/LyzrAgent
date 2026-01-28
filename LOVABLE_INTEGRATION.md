# 🚀 Lovable Integration Guide - Document Processing Platform

## Quick Start for Lovable

Your Document Processing Platform is now **Lovable-ready**! Here's everything you need to integrate it with your Lovable frontend.

## 🔧 Backend Setup (Already Configured)

✅ **CORS configured** for Lovable domains  
✅ **API endpoints** ready for frontend integration  
✅ **TypeScript types** generated  
✅ **WebSocket support** for real-time updates  
✅ **Docker deployment** ready  

## 🌐 API Base URL

- **Local Development**: `http://localhost:8000`
- **Production**: Update with your deployed URL

## 📋 Integration Checklist

### 1. Start Your Backend Server

```bash
# Option A: Local development
cd /Users/rudranshtiwri/Code/LyzrAgent
source venv/bin/activate
export OPENAI_API_KEY="your-openai-key-here"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Option B: Using the deployment script
./deploy.sh local

# Option C: Docker deployment
./deploy.sh docker
```

### 2. Verify Backend is Running

Visit: `http://localhost:8000/health`

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T...",
  "service": "Document Processing Platform"
}
```

### 3. API Documentation

Interactive API docs: `http://localhost:8000/docs`

## 🎯 Key Integration Points

### File Upload Component

```typescript
import { DocumentUploadResponse } from './types/api';

const uploadDocument = async (file: File): Promise<DocumentUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/process-document', {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }
  
  return response.json();
};
```

### Text Processing Component

```typescript
import { ProcessTextRequest, DocumentUploadResponse } from './types/api';

const processText = async (text: string): Promise<DocumentUploadResponse> => {
  const payload: ProcessTextRequest = {
    text_content: text,
    document_type: 'txt'
  };
  
  const response = await fetch('http://localhost:8000/process-text', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  
  return response.json();
};
```

### Real-time Status Updates

```typescript
import { WorkflowStatusResponse } from './types/api';

const useDocumentStatus = (threadId: string) => {
  const [status, setStatus] = useState<WorkflowStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const response = await fetch(`http://localhost:8000/status/${threadId}`);
        const statusData = await response.json();
        setStatus(statusData);
        
        if (statusData.is_complete) {
          setIsLoading(false);
        }
      } catch (error) {
        console.error('Status check failed:', error);
      }
    };
    
    const interval = setInterval(pollStatus, 2000);
    pollStatus(); // Initial call
    
    return () => clearInterval(interval);
  }, [threadId]);
  
  return { status, isLoading };
};
```

### WebSocket Integration

```typescript
import { WebSocketMessage } from './types/api';

const useWebSocket = (documentId: string) => {
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  
  useEffect(() => {
    const websocket = new WebSocket(`ws://localhost:8000/workflow/${documentId}/stream`);
    
    websocket.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      setMessages(prev => [...prev, message]);
    };
    
    websocket.onopen = () => {
      console.log('WebSocket connected');
      setWs(websocket);
    };
    
    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setWs(null);
    };
    
    return () => {
      websocket.close();
    };
  }, [documentId]);
  
  return { messages, ws };
};
```

## 🎨 UI Components Examples

### Document Upload Component

```tsx
import React, { useState } from 'react';
import { DocumentUploadResponse } from './types/api';

const DocumentUploader: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<DocumentUploadResponse | null>(null);
  
  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('http://localhost:8000/process-document', {
        method: 'POST',
        body: formData,
      });
      
      const result = await response.json();
      setResult(result);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };
  
  return (
    <div className="upload-container">
      <input
        type="file"
        accept=".pdf,.docx,.txt,.jpg,.jpeg,.png"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button 
        onClick={handleUpload} 
        disabled={!file || uploading}
        className="upload-btn"
      >
        {uploading ? 'Processing...' : 'Upload Document'}
      </button>
      
      {result && (
        <div className="result">
          <h3>Processing Started!</h3>
          <p>Document ID: {result.document_id}</p>
          <p>Thread ID: {result.thread_id}</p>
          <p>Status: {result.status}</p>
        </div>
      )}
    </div>
  );
};
```

### Processing Status Component

```tsx
import React from 'react';
import { WorkflowStatusResponse } from './types/api';

interface StatusDisplayProps {
  status: WorkflowStatusResponse;
}

const StatusDisplay: React.FC<StatusDisplayProps> = ({ status }) => {
  const getStatusColor = (currentStatus: string) => {
    switch (currentStatus) {
      case 'completed': return 'green';
      case 'failed': return 'red';
      case 'human_review_required': return 'orange';
      case 'processing': return 'blue';
      default: return 'gray';
    }
  };
  
  return (
    <div className="status-display">
      <div className="status-header">
        <h3>Processing Status</h3>
        <span 
          className="status-badge"
          style={{ backgroundColor: getStatusColor(status.current_status) }}
        >
          {status.current_status}
        </span>
      </div>
      
      <div className="status-details">
        <p><strong>Current Agent:</strong> {status.current_agent || 'None'}</p>
        <p><strong>Next Agent:</strong> {status.next_agent || 'None'}</p>
        <p><strong>Complete:</strong> {status.is_complete ? 'Yes' : 'No'}</p>
        <p><strong>Can Continue:</strong> {status.can_continue ? 'Yes' : 'No'}</p>
      </div>
      
      {status.human_interaction && Object.keys(status.human_interaction).length > 0 && (
        <div className="human-review-section">
          <h4>Human Review Required</h4>
          <pre>{JSON.stringify(status.human_interaction, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
```

## 🔒 Security & Environment

### Environment Variables

Make sure these are set in your deployment:

```bash
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here  # Optional
```

### CORS Configuration

Already configured for:
- `http://localhost:3000` (local development)
- `https://*.lovable.dev` (Lovable preview)
- `https://*.lovableproject.com` (Lovable production)

## 🚀 Deployment Options

### Option 1: Local Development
```bash
./deploy.sh local
```

### Option 2: Docker
```bash
./deploy.sh docker
```

### Option 3: Manual
```bash
source venv/bin/activate
export OPENAI_API_KEY="your-key"
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## 📊 Supported Features

✅ **File Upload**: PDF, DOCX, TXT, JPG, JPEG, PNG  
✅ **Text Processing**: Direct text input  
✅ **Real-time Updates**: WebSocket support  
✅ **Human Review**: Interactive review workflow  
✅ **Multi-agent Processing**: 9 specialized AI agents  
✅ **Status Tracking**: Real-time progress monitoring  
✅ **Error Handling**: Comprehensive error responses  

## 🛠️ Troubleshooting

### Backend Not Responding
1. Check if server is running: `curl http://localhost:8000/health`
2. Verify API key is set: `echo $OPENAI_API_KEY`
3. Check server logs for errors

### CORS Issues
- Ensure your Lovable domain is included in the CORS origins
- Check browser console for CORS errors

### File Upload Issues
- Verify file type is supported
- Check file size (no explicit limit set, but consider adding one)
- Ensure `uploads/` directory exists and is writable

## 📞 Support

- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`
- **Logs**: `docker-compose logs` (if using Docker)

## 🎉 You're Ready!

Your Document Processing Platform is now fully integrated and ready for Lovable! Start building your frontend and connect to the API endpoints above.

**Happy coding! 🚀**