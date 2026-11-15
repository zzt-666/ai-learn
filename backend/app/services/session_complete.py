"""Backward-compatible re-export; implementation lives in session_progress. """

from app.services.session_progress import complete_session

__all__ = ["complete_session"]
