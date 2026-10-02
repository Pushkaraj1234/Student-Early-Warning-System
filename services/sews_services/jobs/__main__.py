"""``python -m sews_services.jobs <command>``: see sews_services.jobs.cli."""

from __future__ import annotations

import logging

from sews_services.jobs.cli import main

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
raise SystemExit(main())
