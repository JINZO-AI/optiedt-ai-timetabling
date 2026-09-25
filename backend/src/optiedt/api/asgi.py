"""ASGI entry point: ``uvicorn optiedt.api.asgi:app``."""

from optiedt.api.app import create_app

app = create_app()
