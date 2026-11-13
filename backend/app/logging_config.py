"""Console logging so quiz / Tavily debug lines show under uvicorn --reload."""

from __future__ import annotations

import logging
import sys


_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATEFMT = "%H:%M:%S"


def configure_logging(level: int = logging.INFO) -> None:
    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    # Attach a dedicated console handler on the `app` logger.
    # Uvicorn --reload often owns the root logger; basicConfig alone is unreliable.
    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)

    has_stream = any(
        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) in (sys.stderr, sys.stdout)
        for h in app_logger.handlers
    )
    if not has_stream:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        app_logger.addHandler(handler)

    # Avoid double printing if root also has handlers.
    app_logger.propagate = False

    for name in (
        "app.services.quiz_research",
        "app.services.quiz_service",
        "app.services.tavily_tools",
        "app.routers.quiz",
    ):
        child = logging.getLogger(name)
        child.setLevel(level)
        # Children propagate into `app` (parent), which owns the StreamHandler.
        child.propagate = True
