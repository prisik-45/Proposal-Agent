#!/usr/bin/env python
"""
Startup script for the Proposal Agent API server.
Run with: python run_api.py
"""

import uvicorn
import sys

if __name__ == "__main__":
    # Run on 0.0.0.0:8000 to accept external connections
    # Reload enabled for development
    uvicorn.run(
        "src.api:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
        log_level="info",
        workers=1
    )
