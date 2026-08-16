"""Entry point: python -m backend.run"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn  # noqa: E402

from backend.api import BIND_HOST, BIND_PORT, app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(app, host=BIND_HOST, port=BIND_PORT)
