# 🔗 Complete Lovable Integration Guide

## Step 1: Create Your Lovable Project

1. **Go to Lovable.dev** and create a new project
2. **Choose "React + TypeScript"** template
3. **Name your project**: "Document Processing Platform" or similar

## Step 2: Backend Configuration

### Your FastAPI Backend is Already Ready!
- ✅ Running on: `http://localhost:8000`
- ✅ CORS configured for Lovable domains
- ✅ Simplified endpoints created
- ✅ WebSocket support enabled

### Keep Your Backend Running:
```bash
cd /Users/rudranshtiwri/Code/LyzrAgent
source venv/bin/activate
export OPENAI_API_KEY="your-key-here"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 3: Frontend Components for Lovable

### 1. Main Document Processor Component

Create this in Lovable as `DocumentProcessor.tsx`:

```tsx
import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle, Clock } from 'lucide-react';

interface ProcessingStatus {
  document_id: string;
  status: string;
  progress_percentage: number;
  current_step: string;
  is_complete: boolean;
  requires_human_review: boolean;
  error?: string;
}

interface ProcessingResult {
  success: boolean;
  document_id: string;
  thread_id: string;
  filename: string;
  status: string;
  message: string;
}

const DocumentProcessor: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [result, setResult] = useState<ProcessingResult | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);

  const API_BASE = 'http://localhost:8000';

  // Upload and process document
  const handleUpload = async () => {
    if (!file) return;

    setProcessing(true);
    setStatus(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/upload-and-process`, {
        method: 'POST',
        body: formData,
      });

      const data: ProcessingResult = await response.json();
      setResult(data);

      if (data.success) {
        // Start WebSocket connection for real-time updates
        connectWebSocket(data.document_id);
        // Start polling for status
        pollStatus(data.document_id, data.thread_id);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setProcessing(false);
    }
  };

  // WebSocket connection for real-time updates
  const connectWebSocket = (documentId: string) => {
    const websocket = new WebSocket(`ws://localhost:8000/workflow/${documentId}/stream`);
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket update:', data);
      
      // Handle different message types
      if (data.type === 'processing_completed') {
        setProcessing(false);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);
  };

  // Poll for status updates
  const pollStatus = async (documentId: string, threadId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `${API_BASE}/simple-status/${documentId}?thread_id=${threadId}`
        );
        const statusData: ProcessingStatus = await response.json();
        setStatus(statusData);

        if (statusData.is_complete || statusData.status === 'error') {
          clearInterval(interval);
          setProcessing(false);
        }
      } catch (error) {
        console.error('Status check failed:', error);
        clearInterval(interval);
        setProcessing(false);
      }
    }, 2000);
  };

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [ws]);

  const getStatusIcon = () => {
    if (!status) return <Clock className="w-5 h-5 text-gray-400" />;
    
    switch (status.status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
    }
  };

  const getStatusColor = () => {
    if (!status) return 'bg-gray-200';
    
    switch (status.status) {
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          AI Document Processing Platform
        </h1>
        <p className="text-gray-600">
          Upload documents for intelligent processing with 9 specialized AI agents
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <Upload className="w-5 h-5 mr-2" />
          Upload Document
        </h2>
        
        <div className="space-y-4">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              accept=".pdf,.docx,.txt,.jpg,.png,.xlsx"
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer flex flex-col items-center"
            >
              <FileText className="w-12 h-12 text-gray-400 mb-2" />
              <span className="text-lg font-medium text-gray-700">
                {file ? file.name : 'Choose a file to upload'}
              </span>
              <span className="text-sm text-gray-500 mt-1">
                Supports PDF, DOCX, TXT, JPG, PNG, XLSX
              </span>
            </label>
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || processing}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {processing ? 'Processing...' : 'Upload & Process Document'}
          </button>
        </div>
      </div>

      {/* Processing Status */}
      {(processing || status) && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            {getStatusIcon()}
            <span className="ml-2">Processing Status</span>
          </h2>

          {result && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Document ID:</strong> {result.document_id}
              </p>
              <p className="text-sm text-blue-800">
                <strong>Filename:</strong> {result.filename}
              </p>
            </div>
          )}

          {status && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">
                  Progress: {status.progress_percentage.toFixed(1)}%
                </span>
                <span className="text-sm text-gray-500">
                  Current: {status.current_step}
                </span>
              </div>

              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${getStatusColor()}`}
                  style={{ width: `${status.progress_percentage}%` }}
                ></div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <strong>Status:</strong> {status.status}
                </div>
                <div>
                  <strong>Complete:</strong> {status.is_complete ? 'Yes' : 'No'}
                </div>
              </div>

              {status.requires_human_review && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-yellow-800 font-medium">
                    ⚠️ Human Review Required
                  </p>
                  <p className="text-yellow-700 text-sm">
                    This document requires manual review before completion.
                  </p>
                </div>
              )}

              {status.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-800 font-medium">Error:</p>
                  <p className="text-red-700 text-sm">{status.error}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Agent Status Grid */}
      {status && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">AI Agents Status</h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              'Ingestion Agent',
              'Classification Agent', 
              'Extraction Agent',
              'Validation Agent',
              'Rule Evaluation Agent',
              'Anomaly Detection Agent',
              'Human Review Agent',
              'Audit Learning Agent',
              'Coordinator Agent'
            ].map((agent, index) => (
              <div key={agent} className="p-3 border rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{agent}</span>
                  <div className={`w-3 h-3 rounded-full ${
                    index < (status.progress_percentage / 100) * 9 
                      ? 'bg-green-500' 
                      : 'bg-gray-300'
                  }`}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentProcessor;
```

### 2. Results Viewer Component

Create `ResultsViewer.tsx`:

```tsx
import React, { useState, useEffect } from 'react';
import { FileText, Download, Eye } from 'lucide-react';

interface ExtractedData {
  [key: string]: any;
}

interface ProcessingResults {
  success: boolean;
  document_id: string;
  workflow_id: string;
  status: string;
  extracted_data: ExtractedData;
  validated_data: ExtractedData;
  business_rules_applied: Array<{
    rule_id: string;
    rule_name: string;
    rule_type: string;
    condition: string;
    action: string;
    priority: number;
  }>;
  anomalies_detected: Array<any>;
  human_review_required: boolean;
  processing_time: number;
  confidence_scores: { [key: string]: number };
}

interface ResultsViewerProps {
  threadId: string;
  documentId: string;
}

const ResultsViewer: React.FC<ResultsViewerProps> = ({ threadId, documentId }) => {
  const [results, setResults] = useState<ProcessingResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = 'http://localhost:8000';

  useEffect(() => {
    fetchResults();
  }, [threadId]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/results/${threadId}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch results');
      }

      const data: ProcessingResults = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const downloadResults = () => {
    if (!results) return;
    
    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `results_${documentId}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Loading results...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800">Error: {error}</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <p className="text-gray-600">No results available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Processing Results</h2>
        <button
          onClick={downloadResults}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Download className="w-4 h-4 mr-2" />
          Download Results
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-semibold text-gray-700">Status</h3>
          <p className={`text-lg font-bold ${
            results.status === 'completed' ? 'text-green-600' : 'text-yellow-600'
          }`}>
            {results.status}
          </p>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-semibold text-gray-700">Processing Time</h3>
          <p className="text-lg font-bold text-blue-600">
            {results.processing_time.toFixed(2)}s
          </p>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-semibold text-gray-700">Human Review</h3>
          <p className={`text-lg font-bold ${
            results.human_review_required ? 'text-orange-600' : 'text-green-600'
          }`}>
            {results.human_review_required ? 'Required' : 'Not Required'}
          </p>
        </div>
      </div>

      {/* Extracted Data */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4 flex items-center">
          <FileText className="w-5 h-5 mr-2" />
          Extracted Data
        </h3>
        <div className="bg-gray-50 p-4 rounded-lg overflow-x-auto">
          <pre className="text-sm">
            {JSON.stringify(results.extracted_data, null, 2)}
          </pre>
        </div>
      </div>

      {/* Confidence Scores */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4">Confidence Scores</h3>
        <div className="space-y-3">
          {Object.entries(results.confidence_scores).map(([agent, score]) => (
            <div key={agent} className="flex items-center justify-between">
              <span className="text-sm font-medium capitalize">
                {agent.replace('_', ' ')}
              </span>
              <div className="flex items-center space-x-2">
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${score * 100}%` }}
                  ></div>
                </div>
                <span className="text-sm text-gray-600 w-12">
                  {(score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Business Rules */}
      {results.business_rules_applied.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold mb-4">Business Rules Applied</h3>
          <div className="space-y-3">
            {results.business_rules_applied.map((rule, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium">{rule.rule_name}</h4>
                    <p className="text-sm text-gray-600">{rule.condition}</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    rule.priority === 1 ? 'bg-red-100 text-red-800' :
                    rule.priority === 2 ? 'bg-yellow-100 text-yellow-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    Priority {rule.priority}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Anomalies */}
      {results.anomalies_detected.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold mb-4 text-red-600">
            Anomalies Detected
          </h3>
          <div className="space-y-3">
            {results.anomalies_detected.map((anomaly, index) => (
              <div key={index} className="border border-red-200 rounded-lg p-3 bg-red-50">
                <pre className="text-sm text-red-800">
                  {JSON.stringify(anomaly, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultsViewer;
```

## Step 4: Main App Component

Update your main `App.tsx` in Lovable:

```tsx
import React, { useState } from 'react';
import DocumentProcessor from './components/DocumentProcessor';
import ResultsViewer from './components/ResultsViewer';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

function App() {
  const [activeThreadId, setActiveThreadId] = useState<string>('');
  const [activeDocumentId, setActiveDocumentId] = useState<string>('');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8">
        <Tabs defaultValue="processor" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="processor">Document Processor</TabsTrigger>
            <TabsTrigger value="results" disabled={!activeThreadId}>
              Results Viewer
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="processor" className="mt-6">
            <DocumentProcessor 
              onProcessingStarted={(documentId, threadId) => {
                setActiveDocumentId(documentId);
                setActiveThreadId(threadId);
              }}
            />
          </TabsContent>
          
          <TabsContent value="results" className="mt-6">
            {activeThreadId && (
              <ResultsViewer 
                threadId={activeThreadId}
                documentId={activeDocumentId}
              />
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;
```

## Step 5: Environment Configuration

In Lovable, you might need to configure environment variables. Create a `.env.local` file:

```env
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_BASE_URL=ws://localhost:8000
```

## Step 6: Package Dependencies

Make sure these packages are installed in your Lovable project:

```json
{
  "dependencies": {
    "lucide-react": "^0.263.1",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0"
  }
}
```

## Step 7: Testing Your Integration

1. **Start your FastAPI backend** (already running)
2. **In Lovable**, use the components above
3. **Test file upload** with a sample document
4. **Watch real-time updates** via WebSocket
5. **View processing results** in the Results tab

## Step 8: Deployment Considerations

### For Production:
1. **Update API URLs** to your deployed backend
2. **Configure CORS** for your Lovable production domain
3. **Add authentication** if needed
4. **Implement error boundaries** for better UX
5. **Add loading states** and retry mechanisms

Your LangGraph workflow is now fully integrated with Lovable! 🚀