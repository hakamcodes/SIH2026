"""Re-export point for `uvicorn lmd.main:app`."""
from lmd.api.main import app

__all__ = ["app"]
