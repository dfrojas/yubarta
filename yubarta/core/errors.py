"""Incident domain errors."""

from __future__ import annotations


class IncidentError(Exception):
    """Base incident domain error."""


class InvalidTransitionError(IncidentError):
    """Raised when a state transition is not allowed."""


class ConcurrentModificationError(IncidentError):
    """Raised when OCC version check fails."""
