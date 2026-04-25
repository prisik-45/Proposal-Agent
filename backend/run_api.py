#!/usr/bin/env python
"""
Startup script for the Proposal Agent API server.
Run with: python run_api.py
"""

import uvicorn
import sys
import os

if __name__ == "__main__":
    # Render assigns the PORT environment variable. We default to 8000 for local dev.
    port = int(os.environ.get("PORT", 8000))
    
    # Run on 0.0.0.0 to accept external connections (necessary for Render/Docker)
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        workers=1
    )
