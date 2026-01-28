#!/usr/bin/env python3
"""
Startup script for Railway deployment with error handling
"""

import os
import sys
import logging
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check required environment variables"""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("Environment variables check passed")
    return True

def main():
    """Main startup function"""
    logger.info("Starting Document Processing Platform...")
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed")
        sys.exit(1)
    
    # Get port from environment
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    
    try:
        # Import the app
        from api.main import app
        logger.info("FastAPI app imported successfully")
        
        # Start uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )
    except ImportError as e:
        logger.error(f"Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()