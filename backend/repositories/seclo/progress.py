"""
Progress reporting utilities.
"""

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
        self.total_steps = 0
        self.current_steps = 0
        self.message = ""
        self.subprogresses: List[Tuple["ProgressReport", str]] = []
        self.parent: Optional[ProgressReport] = None
        self.taskmanager = taskmanager
        self.running = False

    def set_parent(self: Self, parent: "ProgressReport"):
        "Sets this progress' parent (for propagating messages and such)"
        self.parent = parent

    def set_steps(self: Self, steps: int) -> Self:
        """
        Sets how many steps this progress will have.
        Allows percentage calculations and interacting with progress through increments.
        """
        logger.debug("SET STEPS %d", steps)
        self.total_steps = steps
        if self.total_steps > self.current_steps:
            self.running=True
        return self

    async def compose(self: Self, subprogress: "ProgressReport", message: str = "") -> Self:
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
        self.running=True
        if self.parent is not None:
            await self.parent.propagate_progress_to_parent()
        return self

    async def set_progress(self, step: float, message: str = "") -> Self:
        """
        Sets the current progress status.
        Parameters:
            step (float): How many steps have executed.
            message (str): Status to display.
        """
        if (len(self.subprogresses)) > 0:
            raise AttributeError("Can't set progress on a composed report")
        self.current_steps = step
        self.message = message
        if self.current_steps < self.total_steps:
            self.running=True
        if self.parent is not None:
            await self.parent.propagate_progress_to_parent()

        logger.debug(
            "SET PROGRESS %d %s", self.get_progress()['progress'], f"({message})" if message else ""
        )
        return self

    async def increase_progress(self: Self, message: Optional[str] = None) -> Self:
        """
        Increments this progress' completion percentage by one step.
        Parameters:
            message (str): Status to display.
        """
        if (len(self.subprogresses)) > 0:
            raise AttributeError("Can't set progress on a composed report")
        self.current_steps += 1
        if not self.running:
            self.running = True
        if message is not None:
            self.message = message

        if self.parent is not None:
            await self.parent.propagate_progress_to_parent()

        logger.debug(
            "INCREASE PROGRESS: %.2f%% %s",
            (100 * self.get_progress()['progress']),
            f"({message})" if message else "",
        )
        return self

    async def set_message(self: Self, message: str) -> Self:
        """
        Overrides the current progress status message.
        Parameters:
            message (str): Status to display.
        """
        logger.debug("SET MESSAGE: %s", message)
        self.message = message

        if self.parent is not None:
            await self.parent.propagate_progress_to_parent()
        return self

    async def set_completion(self: Self, message: str) -> Self:
        """
        Marks this progress as done.
        Parameters:
            message (str): Status to display.
        """
        logger.debug("SET COMPLETION %s", f"({message})" if message else "")
        self.running = False
        self.message = message

        if self.parent is not None:
            await self.parent.propagate_progress_to_parent()
        if self.taskmanager is not None:
            await self.taskmanager.update_task_slot_progress(self.get_progress())
        return self

    def get_progress(self: Self) -> Dict:
        """
        Calculates this progress' status.
        Returns:
            Dict: {'progress': float, 'message': str, 'status': str}
        """
        current_progress = (self.current_steps / self.total_steps) if self.total_steps > 0 else 0.0
        if current_progress > 0 and not self.running:
            return {
                "progress": 1.0,
                "running": False,
                "message": self.message
            }
        if len(self.subprogresses) > 0:
            progress_step = (
                (1 / self.total_steps) if self.total_steps > 0 else (1 / len(self.subprogresses))
            )
            current_progress = 0.0
            self.running = False
            valid_subprogresses = []
            for progress in self.subprogresses:
                current = progress[0].get_progress()
                if current["progress"] > 0 and not progress[0].running:
                    current_progress += 1 * progress_step
                else:
                    current_progress += current["progress"] * progress_step
                    self.running = self.running or current["running"]
                    valid_subprogresses.append(progress)
            if current_progress > 0 and not self.running:
                return {
                    "progress": 1.0,
                    "running": False,
                    "message": self.message
                }
            return {
                "progress": current_progress,
                "message": self.message,
                "running": self.running,
                "subprogresses": 
                    [{"name": s, "progress": p.get_progress()} for p, s in valid_subprogresses]
            }
        return {
            "progress": current_progress,
            "message": self.message,
            "running": self.running,
        }

    async def propagate_progress_to_parent(self: Self):
        "Propagates current progress up the chain to parent and eventually to user"
        progress = self.get_progress()
        if self.parent is not None:
            await self.parent.propagate_progress_to_parent()
        if self.taskmanager is not None:
            await self.taskmanager.update_task_slot_progress(progress)
