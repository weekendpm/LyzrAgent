// API Configuration for Lovable Integration
// Copy this file to your Lovable project

export const API_CONFIG = {
  // Backend URLs
  BASE_URL: 'http://localhost:8000',
  WS_BASE_URL: 'ws://localhost:8000',
  
  // API Endpoints
  ENDPOINTS: {
    HEALTH: '/health',
    UPLOAD_AND_PROCESS: '/upload-and-process',
    PROCESS_TEXT: '/process-text',
    SIMPLE_STATUS: '/simple-status',
    STATUS: '/status',
    RESULTS: '/results',
    WEBSOCKET: '/workflow'
  },
  
  // Supported file types
  SUPPORTED_FILES: {
    TYPES: ['.pdf', '.docx', '.txt', '.jpg', '.png', '.xlsx'],
    MIME_TYPES: [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain',
      'image/jpeg',
      'image/png',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ]
  },
  
  // Polling intervals
  STATUS_POLL_INTERVAL: 2000, // 2 seconds
  
  // Agent names for UI display
  AGENTS: [
    'Ingestion Agent',
    'Classification Agent', 
    'Extraction Agent',
    'Validation Agent',
    'Rule Evaluation Agent',
    'Anomaly Detection Agent',
    'Human Review Agent',
    'Audit Learning Agent',
    'Coordinator Agent'
  ]
};

// API Service Functions
export class DocumentProcessingAPI {
  private baseUrl: string;
  
  constructor(baseUrl: string = API_CONFIG.BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string; service: string }> {
    const response = await fetch(`${this.baseUrl}${API_CONFIG.ENDPOINTS.HEALTH}`);
    return response.json();
  }

  // Upload and process document
  async uploadAndProcess(file: File): Promise<{
    success: boolean;
    document_id: string;
    thread_id: string;
    filename: string;
    status: string;
    message: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}${API_CONFIG.ENDPOINTS.UPLOAD_AND_PROCESS}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Process text directly
  async processText(textContent: string, fileType: string = 'text'): Promise<{
    success: boolean;
    document_id: string;
    thread_id: string;
    status: string;
    message: string;
  }> {
    const response = await fetch(`${this.baseUrl}${API_CONFIG.ENDPOINTS.PROCESS_TEXT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text_content: textContent,
        file_type: fileType,
      }),
    });

    if (!response.ok) {
      throw new Error(`Text processing failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Get simplified status
  async getSimpleStatus(documentId: string, threadId: string): Promise<{
    document_id: string;
    status: string;
    progress_percentage: number;
    current_step: string;
    is_complete: boolean;
    requires_human_review: boolean;
    error?: string;
  }> {
    const response = await fetch(
      `${this.baseUrl}${API_CONFIG.ENDPOINTS.SIMPLE_STATUS}/${documentId}?thread_id=${threadId}`
    );

    if (!response.ok) {
      throw new Error(`Status check failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Get full results
  async getResults(threadId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}${API_CONFIG.ENDPOINTS.RESULTS}/${threadId}`);

    if (!response.ok) {
      throw new Error(`Results fetch failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Create WebSocket connection
  createWebSocket(documentId: string): WebSocket {
    return new WebSocket(`${API_CONFIG.WS_BASE_URL}${API_CONFIG.ENDPOINTS.WEBSOCKET}/${documentId}/stream`);
  }
}

// Export singleton instance
export const documentAPI = new DocumentProcessingAPI();

// Utility functions
export const utils = {
  // Format file size
  formatFileSize: (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // Check if file type is supported
  isFileSupported: (file: File): boolean => {
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    return API_CONFIG.SUPPORTED_FILES.TYPES.includes(extension) ||
           API_CONFIG.SUPPORTED_FILES.MIME_TYPES.includes(file.type);
  },

  // Get progress color based on percentage
  getProgressColor: (percentage: number): string => {
    if (percentage < 30) return 'bg-red-500';
    if (percentage < 70) return 'bg-yellow-500';
    return 'bg-green-500';
  },

  // Format processing time
  formatProcessingTime: (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(1)}s`;
  }
};