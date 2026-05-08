"""
Progress reporting utilities.
"""

import asyncio
import logging
from typing import List, Self, Dict, Tuple, Optional

from domainlogic.taskmanager import TaskManager

logger = logging.getLogger(__name__)


class ProgressReport:
    """
    A class for reporting the execution status of a long SECLO call.
    Can be composed for granular progress control of complex operations.
    Parameters:
        taskmanager: Task manager to report asynchronously to caller (only if main progress)
    """

    def __init__(self, taskmanager: Optional[TaskManager] = None):
        self.progress = 0.0
        self.steps = 0
        self.message = ""
        self.done = False
        self.subprogresses: List[Tuple["ProgressReport", str]] = []
        self.parent: Optional[ProgressReport] = None
        self.taskmanager = taskmanager

    def set_parent(self: Self, parent: "ProgressReport"):
        self.parent = parent

    def set_steps(self: Self, steps: int) -> Self:
        """
        Sets how many steps this progress will have.
        Allows percentage calculations and interacting with progress through increments.
        """
        logger.debug("SET STEPS %d", steps)
        self.steps = steps
        self.done = False
        return self

    def compose(self: Self, subprogress: "ProgressReport", message: str = "") -> Self:
        """
        Registers a child for this progress.
        This progress' completion percentage will be evenly distributed across each subprogress.
        Parameters:
            subprogress (ProgressReport): a progress to compose.
            message (str): Message to append before the subprogress message while it's reporting.
        """
        logger.debug("COMPOSE %s", f"({message})" if message else "")
        self.subprogresses.append((subprogress, message))
        subprogress.set_parent(self)
        self.done = False
        self.get_progress()
        return self

    def set_progress(self, step: float, message: str = "") -> Self:
        """
        Sets the current progress status.
        Parameters:
            step (float): How many steps have executed.
            message (str): Status to display.
        """
        if (len(self.subprogresses)) > 0:
            raise AttributeError("Can't set progress on a composed report")
        self.progress = step / self.steps
        self.message = message
        self.done = False

        if self.parent is not None:
            self.parent.notify_progress_to_parent()

        logger.debug(
            "SET PROGRESS %d %s", self.progress, f"({message})" if message else ""
        )
        return self

    def increase_progress(self: Self, message: Optional[str] = None) -> Self:
        """
        Increments this progress' completion percentage by one step.
        Parameters:
            message (str): Status to display.
        """
        if (len(self.subprogresses)) > 0:
            raise AttributeError("Can't set progress on a composed report")
        self.progress += 1 / self.steps
        if message is not None:
            self.message = message
        self.done = False

        if self.parent is not None:
            self.parent.notify_progress_to_parent()

        logger.debug(
            "INCREASE PROGRESS: %.2f%% %s",
            (100 * self.progress),
            f"({message})" if message else "",
        )
        return self

    def set_message(self: Self, message: str) -> Self:
        """
        Overrides the current progress status message.
        Parameters:
            message (str): Status to display.
        """
        logger.debug("SET MESSAGE: %s", message)
        self.message = message

        if self.parent is not None:
            self.parent.notify_progress_to_parent()
        return self

    def set_completion(self: Self, message: str) -> Self:
        """
        Marks this progress as done.
        Parameters:
            message (str): Status to display.
        """
        logger.debug("SET COMPLETION %s", f"({message})" if message else "")
        self.progress = 1
        self.done = True
        self.message = message

        if self.parent is not None:
            self.parent.notify_progress_to_parent()
        if self.taskmanager is not None:
            self.taskmanager.update_task_slot_progress(self.get_progress())
        return self

    def get_progress(self: Self) -> Dict:
        """
        Calculates this progress' status.
        Returns:
            Dict: {'progress': float, 'message': str}
        """
        if self.subprogresses:
            self.progress = 0
            progress_step = (
                1 / self.steps if self.steps > 0 else 1 / len(self.subprogresses)
            )
            if not self.done:
                for progress, message in self.subprogresses:
                    if progress.is_complete():
                        self.progress += 1 * progress_step
                    else:
                        current = progress.get_progress()
                        self.progress += current["progress"] * progress_step
                        self.message = message + (
                            (": " + current["message"])
                            if len(current["message"]) > 0
                            else ""
                        )
                        break
                else:
                    self.message = self.subprogresses[-1][1] + (
                        (": " + self.subprogresses[-1][0].message)
                        if len(self.subprogresses[-1][0].message)
                        else ""
                    )
                    if self.steps != 0 and self.steps <= len(self.subprogresses):
                        self.done = True
        return {"progress": self.progress, "message": self.message}

    def is_complete(self: Self) -> bool:
        """Returns whether this progress is completed or not."""
        return self.done

    def notify_progress_to_parent(self: Self):
        progress = self.get_progress()
        if self.parent is not None:
            self.parent.notify_progress_to_parent()
        if self.taskmanager is not None:
            self.taskmanager.update_task_slot_progress(progress)
