#!/usr/bin/env python3
"""
Start script for SpendSense Web Backend
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    print("🚀 Starting SpendSense Web Backend...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📋 API documentation at: http://localhost:8000/docs")
    print("🔐 Login credentials: SpendSense / 12345")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 SpendSense Web Backend stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)