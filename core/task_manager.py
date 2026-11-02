"""Backward-compatible import facade for the Core task manager."""

from .tasks.task_manager import LocalTaskManager, TRANSITIONS

__all__ = ["LocalTaskManager", "TRANSITIONS"]
