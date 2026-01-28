// TypeScript types for Document Processing Platform API
// Generated for Lovable frontend integration

export interface DocumentUploadResponse {
  success: boolean;
  document_id: string;
  workflow_id: string;
  thread_id: string;
  message: string;
  status: string;
  requires_human_review: boolean;
}

export interface WorkflowStatusResponse {
  workflow_id: string;
  document_id: string;
  current_status: string;
  current_agent?: string;
  next_agent?: string;
  progress: Record<string, any>;
  timing: Record<string, any>;
  human_interaction: Record<string, any>;
  quality_metrics: Record<string, any>;
  is_complete: boolean;
  can_continue: boolean;
}

export interface ProcessingResultResponse {
  success: boolean;
  document_id: string;
  workflow_id: string;
  status: string;
  extracted_data: Record<string, any>;
  validated_data: Record<string, any>;
  business_rules_applied: BusinessRule[];
  anomalies_detected: Anomaly[];
  human_review_required: boolean;
  processing_time: number;
  confidence_scores: Record<string, number>;
}

export interface BusinessRule {
  rule_id: string;
  rule_name: string;
  applied: boolean;
  result: any;
  confidence: number;
}

export interface Anomaly {
  anomaly_id: string;
  type: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  affected_fields: string[];
}

export interface HumanReviewRequest {
  decision: 'approve' | 'reject' | 'modify' | 'escalate';
  feedback: string;
  reviewer: string;
  modifications?: Record<string, any>;
}

export interface HumanReviewContext {
  document_id: string;
  review_request: {
    request_id: string;
    reason: string;
    priority: string;
    requested_by: string;
    timestamp: string;
  };
  document_info: {
    type: string;
    file_type: string;
    content_preview: string;
  };
  extracted_data: Record<string, any>;
  validation_issues: Record<string, any>;
  anomalies: Anomaly[];
  business_rules: BusinessRule[];
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  service: string;
}

// WebSocket message types
export interface WebSocketMessage {
  type: 'processing_started' | 'processing_completed' | 'processing_failed' | 
        'human_review_required' | 'processing_error' | 'status_update' | 
        'human_review_submitted' | 'ping' | 'pong';
  document_id?: string;
  timestamp: string;
  [key: string]: any;
}

export interface ProcessingStartedMessage extends WebSocketMessage {
  type: 'processing_started';
  document_id: string;
  filename?: string;
  content_length?: number;
}

export interface ProcessingCompletedMessage extends WebSocketMessage {
  type: 'processing_completed';
  document_id: string;
  status: string;
  requires_human_review: boolean;
}

export interface ProcessingFailedMessage extends WebSocketMessage {
  type: 'processing_failed';
  document_id: string;
  status: string;
  requires_human_review: boolean;
}

export interface ProcessingErrorMessage extends WebSocketMessage {
  type: 'processing_error';
  document_id: string;
  error: string;
}

export interface HumanReviewRequiredMessage extends WebSocketMessage {
  type: 'human_review_required';
  document_id: string;
  review_request: {
    request_id: string;
    reason: string;
    priority: string;
  };
}

// API Client types
export interface ApiClientConfig {
  baseUrl: string;
  timeout?: number;
  headers?: Record<string, string>;
}

export interface ProcessTextRequest {
  text_content: string;
  document_type?: string;
}

export interface ApiError {
  detail: string | { type: string; loc: string[]; msg: string; input: any }[];
}

// Supported file types
export type SupportedFileType = 'pdf' | 'docx' | 'txt' | 'jpg' | 'jpeg' | 'png';

// Processing status types
export type ProcessingStatus = 
  | 'processing'
  | 'completed' 
  | 'failed'
  | 'human_review_required'
  | 'human_review_completed'
  | 'cancelled';

// Agent types
export type AgentType = 
  | 'ingestion'
  | 'classification'
  | 'extraction'
  | 'validation'
  | 'rule_evaluation'
  | 'anomaly_detection'
  | 'human_review'
  | 'audit_learning'
  | 'coordinator';

// Document types
export interface DocumentInfo {
  id: string;
  file_type: SupportedFileType;
  content: string;
  metadata: Record<string, any>;
}

// Workflow configuration
export interface WorkflowConfig {
  max_retries: number;
  timeout_seconds: number;
  enable_human_review: boolean;
  confidence_threshold: number;
  anomaly_threshold: number;
}

// Quality metrics
export interface QualityMetrics {
  overall_confidence: number;
  extraction_accuracy: number;
  validation_score: number;
  processing_time: number;
  human_review_rate: number;
}

// Audit information
export interface AuditInfo {
  workflow_id: string;
  document_id: string;
  started_at: string;
  completed_at?: string;
  agents_executed: string[];
  human_reviews: number;
  final_status: ProcessingStatus;
  quality_metrics: QualityMetrics;
}