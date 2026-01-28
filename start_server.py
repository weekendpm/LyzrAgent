#!/usr/bin/env python3
"""
Simple startup script for the Document Processing Platform.
Handles environment validation and server startup.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_virtual_environment():
    """Check if running in virtual environment"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
        return True
    else:
        print("⚠️  Not running in virtual environment")
        print("   Consider activating your virtual environment:")
        print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'langgraph', 'langchain', 'fastapi', 'uvicorn', 
        'pydantic', 'dotenv', 'aiofiles'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("   Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages installed")
    return True

def check_environment_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("⚠️  .env file not found")
        print("   Create .env file with your API keys:")
        print("   LLM_PROVIDER=openai")
        print("   OPENAI_API_KEY=your-api-key-here")
        return False
    
    # Check for API key
    with open(env_file) as f:
        content = f.read()
        
    if "OPENAI_API_KEY=" in content or "ANTHROPIC_API_KEY=" in content:
        print("✅ Environment file configured")
        return True
    else:
        print("⚠️  API keys not configured in .env file")
        print("   Add your LLM provider API key to .env")
        return False

def create_directories():
    """Create required directories"""
    directories = ["uploads", "audit_logs", "learning_data"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Required directories created")

def main():
    """Main startup function"""
    print("🚀 Document Processing Platform Startup")
    print("=" * 50)
    
    # Run checks
    checks_passed = True
    
    if not check_python_version():
        checks_passed = False
    
    check_virtual_environment()  # Warning only
    
    if not check_dependencies():
        checks_passed = False
    
    env_configured = check_environment_file()
    if not env_configured:
        checks_passed = False
    
    if not checks_passed:
        print("\n❌ Startup checks failed. Please fix the issues above.")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    print("\n✅ All checks passed!")
    
    # Ask user what to do
    print("\nWhat would you like to do?")
    print("1. Run test workflow")
    print("2. Start API server")
    print("3. Start API server with reload (development)")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        print("\n🧪 Running test workflow...")
        subprocess.run([sys.executable, "test_workflow.py"])
    
    elif choice == "2":
        print("\n🌐 Starting API server...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "api.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
    
    elif choice == "3":
        print("\n🔄 Starting API server with reload...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "api.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    
    elif choice == "4":
        print("👋 Goodbye!")
        sys.exit(0)
    
    else:
        print("❌ Invalid choice")
        sys.exit(1)

if __name__ == "__main__":
    main()