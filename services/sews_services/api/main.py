"""ASGI entry point: ``uvicorn sews_services.api.main:app`` (run from the repository root).

Settings come from environment variables (sews_services.config); startup fails on unsafe
configuration, e.g. a development process pointed at a hosted database.
"""

from __future__ import annotations

import logging

from sews_services.api.app import create_app
from sews_services.config import load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = create_app(load_settings())
