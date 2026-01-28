"""
Configuration settings for the document processing platform.
Centralized configuration management with environment variable support.
"""

import os
from typing import Dict, Any, List, Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    
    # For future database integration
    database_url: str = Field(default="sqlite:///./documents.db", env="DATABASE_URL")
    echo_sql: bool = Field(default=False, env="DATABASE_ECHO")
    
    class Config:
        env_prefix = "DB_"


class LLMSettings(BaseSettings):
    """LLM configuration settings"""
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.1, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=4000, env="OPENAI_MAX_TOKENS")
    
    # Anthropic settings
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    anthropic_temperature: float = Field(default=0.1, env="ANTHROPIC_TEMPERATURE")
    anthropic_max_tokens: int = Field(default=4000, env="ANTHROPIC_MAX_TOKENS")
    
    # Default provider
    default_provider: str = Field(default="openai", env="LLM_PROVIDER")
    
    class Config:
        env_prefix = "LLM_"


class ProcessingSettings(BaseSettings):
    """Document processing configuration"""
    
    # File processing
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    supported_file_types: List[str] = Field(
        default=["pdf", "docx", "txt", "jpg", "jpeg", "png"],
        env="SUPPORTED_FILE_TYPES"
    )
    upload_directory: str = Field(default="uploads", env="UPLOAD_DIRECTORY")
    
    # OCR settings
    enable_ocr: bool = Field(default=True, env="ENABLE_OCR")
    tesseract_path: Optional[str] = Field(default=None, env="TESSERACT_PATH")
    
    # Processing thresholds
    confidence_threshold: float = Field(default=0.8, env="CONFIDENCE_THRESHOLD")
    auto_approve_threshold: float = Field(default=0.95, env="AUTO_APPROVE_THRESHOLD")
    require_review_threshold: float = Field(default=0.6, env="REQUIRE_REVIEW_THRESHOLD")
    escalation_threshold: float = Field(default=0.3, env="ESCALATION_THRESHOLD")
    
    # Anomaly detection
    enable_anomaly_detection: bool = Field(default=True, env="ENABLE_ANOMALY_DETECTION")
    anomaly_threshold: float = Field(default=0.7, env="ANOMALY_THRESHOLD")
    
    # Business rules
    enable_business_rules: bool = Field(default=True, env="ENABLE_BUSINESS_RULES")
    
    # Human review
    enable_human_review: bool = Field(default=True, env="ENABLE_HUMAN_REVIEW")
    
    # Processing timeouts
    max_processing_time: int = Field(default=300, env="MAX_PROCESSING_TIME")  # 5 minutes
    agent_timeout: int = Field(default=60, env="AGENT_TIMEOUT")  # 1 minute per agent
    
    class Config:
        env_prefix = "PROCESSING_"


class APISettings(BaseSettings):
    """API configuration settings"""
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    reload: bool = Field(default=False, env="API_RELOAD")
    
    # CORS settings
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")
    
    # Security
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    secret_key: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    class Config:
        env_prefix = "API_"


class LoggingSettings(BaseSettings):
    """Logging configuration settings"""
    
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_rotation: bool = Field(default=True, env="LOG_ROTATION")
    log_max_size: str = Field(default="10MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    class Config:
        env_prefix = "LOG_"


class AuditSettings(BaseSettings):
    """Audit and monitoring settings"""
    
    # Audit logging
    enable_audit_logging: bool = Field(default=True, env="ENABLE_AUDIT_LOGGING")
    audit_log_directory: str = Field(default="audit_logs", env="AUDIT_LOG_DIRECTORY")
    
    # Metrics collection
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_retention_days: int = Field(default=30, env="METRICS_RETENTION_DAYS")
    
    # Learning and improvement
    enable_learning: bool = Field(default=True, env="ENABLE_LEARNING")
    learning_data_directory: str = Field(default="learning_data", env="LEARNING_DATA_DIRECTORY")
    
    class Config:
        env_prefix = "AUDIT_"


class Settings(BaseSettings):
    """Main application settings"""
    
    # Application info
    app_name: str = Field(default="Document Processing Platform", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    processing: ProcessingSettings = ProcessingSettings()
    api: APISettings = APISettings()
    logging: LoggingSettings = LoggingSettings()
    audit: AuditSettings = AuditSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def get_workflow_config(self) -> Dict[str, Any]:
        """Get workflow configuration dictionary"""
        return {
            # LLM configuration
            "llm_provider": self.llm.default_provider,
            "model_name": (
                self.llm.openai_model if self.llm.default_provider == "openai" 
                else self.llm.anthropic_model
            ),
            "temperature": (
                self.llm.openai_temperature if self.llm.default_provider == "openai"
                else self.llm.anthropic_temperature
            ),
            "max_tokens": (
                self.llm.openai_max_tokens if self.llm.default_provider == "openai"
                else self.llm.anthropic_max_tokens
            ),
            
            # Processing configuration
            "enable_ocr": self.processing.enable_ocr,
            "enable_human_review": self.processing.enable_human_review,
            "confidence_threshold": self.processing.confidence_threshold,
            "max_processing_time": self.processing.max_processing_time,
            "supported_file_types": self.processing.supported_file_types,
            "max_file_size": self.processing.max_file_size,
            
            # Business rules configuration
            "enable_business_rules": self.processing.enable_business_rules,
            "enable_anomaly_detection": self.processing.enable_anomaly_detection,
            "anomaly_threshold": self.processing.anomaly_threshold,
            
            # Human review configuration
            "auto_approve_threshold": self.processing.auto_approve_threshold,
            "require_review_threshold": self.processing.require_review_threshold,
            "escalation_threshold": self.processing.escalation_threshold,
            
            # Audit configuration
            "enable_audit_logging": self.audit.enable_audit_logging,
            "audit_log_directory": self.audit.audit_log_directory,
            "enable_learning": self.audit.enable_learning
        }
    
    def validate_settings(self) -> List[str]:
        """Validate settings and return list of issues"""
        issues = []
        
        # Check LLM API keys
        if self.llm.default_provider == "openai" and not self.llm.openai_api_key:
            issues.append("OpenAI API key is required when using OpenAI as LLM provider")
        
        if self.llm.default_provider == "anthropic" and not self.llm.anthropic_api_key:
            issues.append("Anthropic API key is required when using Anthropic as LLM provider")
        
        # Check file processing settings
        if self.processing.max_file_size <= 0:
            issues.append("Max file size must be positive")
        
        if not self.processing.supported_file_types:
            issues.append("At least one supported file type must be specified")
        
        # Check thresholds
        thresholds = [
            ("confidence_threshold", self.processing.confidence_threshold),
            ("auto_approve_threshold", self.processing.auto_approve_threshold),
            ("require_review_threshold", self.processing.require_review_threshold),
            ("escalation_threshold", self.processing.escalation_threshold),
            ("anomaly_threshold", self.processing.anomaly_threshold)
        ]
        
        for name, value in thresholds:
            if not 0.0 <= value <= 1.0:
                issues.append(f"{name} must be between 0.0 and 1.0")
        
        # Check directory permissions
        directories = [
            self.processing.upload_directory,
            self.audit.audit_log_directory,
            self.audit.learning_data_directory
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create directory {directory}: {e}")
        
        return issues


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get global settings instance"""
    return settings


def validate_environment() -> bool:
    """Validate environment configuration"""
    issues = settings.validate_settings()
    
    if issues:
        print("❌ Configuration Issues Found:")
        for issue in issues:
            print(f"  • {issue}")
        return False
    else:
        print("✅ Configuration validated successfully")
        return True


if __name__ == "__main__":
    # Validate configuration when run directly
    print("🔧 Validating Configuration...")
    is_valid = validate_environment()
    
    if is_valid:
        print("\n📋 Current Configuration:")
        print(f"  Environment: {settings.environment}")
        print(f"  LLM Provider: {settings.llm.default_provider}")
        print(f"  Debug Mode: {settings.debug}")
        print(f"  API Port: {settings.api.port}")
        print(f"  Max File Size: {settings.processing.max_file_size / (1024*1024):.1f}MB")
        print(f"  Supported Types: {', '.join(settings.processing.supported_file_types)}")
    else:
        exit(1)