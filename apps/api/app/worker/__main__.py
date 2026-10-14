"""Entry point for running the worker: python -m app.worker"""
import asyncio

from app.core.logging import setup_logging
from app.worker.pipeline import worker_loop

setup_logging()
asyncio.run(worker_loop())
