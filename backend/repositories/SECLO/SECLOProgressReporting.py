import logging
from threading import Lock
from typing import List, Self, Dict, Tuple

from domainlogic.taskmanager import TaskManager

logger = logging.getLogger(__name__)
class ProgressReport():
    def __init__(self, isComposable:bool = False, taskmanager: TaskManager | None = None):
        self.progress = 0.0
        self.steps = 0
        self.message = ''
        self.checked = Lock()
        self.done = False
        self.subprogresses: List[Tuple['ProgressReport', str]] = []
        if taskmanager: 
            self.taskmanager = taskmanager

    def __set_parent(self: Self, parent: 'ProgressReport'):
        self.parent = parent

    def setSteps(self: Self, steps: int) -> Self:
        logger.debug(f'SET STEPS {steps}')
        self.steps = steps
        self.done = False
        return self
    
    def compose(self: Self, subprogress: 'ProgressReport', message: str = "") -> Self:
        logger.debug(f"COMPOSE {f'({message})' if message else ''}")
        self.subprogresses.append((subprogress, message))
        subprogress.__set_parent(self)
        self.done=False
        progress = self.getProgress()
        if hasattr(self, 'parent'): self.parent.__notifyProgress(self)
        return self
    
    def setProgress(self, step: float, message) -> Self:
        if (len(self.subprogresses)) > 0:
            raise AttributeError("Can't set progress on a composed report")
        self.progress = step / self.steps
        self.message = message
        self.done = False

        if self.checked.locked():
            self.checked.release() 

        if hasattr(self, 'parent'):
            self.parent.__notifyProgress(self)

        logger.debug(f'SET PROGRESS {self.progress} {f'({message})' if message else ''}')
        return self 

    def increaseProgress(self: Self, step:int , message: str | None = None) -> Self:
        if (len(self.subprogresses)) > 0:
            raise AttributeError("Can't set progress on a composed report")
        self.progress += 1/self.steps
        if message != None:
            self.message = message
        self.done = False

        if self.checked.locked():
            self.checked.release()  

        if hasattr(self, 'parent'):
            self.parent.__notifyProgress(self)  

        logger.debug(f'INCREASE PROGRESS: {(100*self.progress):.2f}% {f'({message})' if message else ''}')
        return self        
    
    def setMessage(self: Self, message: str) -> Self:
        logger.debug(f'SET MESSAGE: {message}')
        self.message = message
        if self.checked.locked():
            self.checked.release()
        if hasattr(self, 'parent'):
            self.parent.__notifyProgress(self)
        return self
    
    def setCompletion(self: Self, message: str) -> Self:
        logger.debug(f'SET COMPLETION {f'({message})' if message else ''}')
        self.progress = 1
        self.done = True
        self.message = message
        if self.checked.locked():
            self.checked.release()  
        if hasattr(self, 'parent'):
            self.parent.__notifyProgress(self)
        if hasattr(self, 'taskmanager'):
            self.taskmanager.updateTaskSlotProgress(self.getProgress())            
        return self

    def getProgress(self: Self) -> Dict:
        if self.subprogresses:
            self.progress = 0
            progressStep = 1/self.steps if self.steps > 0 else 1/len(self.subprogresses)
            for (progress, message) in self.subprogresses:  
                if progress.getCompletion():
                    self.progress += 1 * progressStep
                else:
                    currentProgress = progress.getProgress()  
                    self.progress += currentProgress['progress'] * progressStep
                    self.message = message + ((": " + currentProgress['message']) if len(currentProgress['message'])>0 else "")
                    break
            else:
                self.message = self.subprogresses[-1][1] + ((": " + self.subprogresses[-1][0].message) if len(self.subprogresses[-1][0].message) else "")
                if self.steps != 0 and self.steps <= len(self.subprogresses):
                    self.done = True
        else:
            #self.checked.acquire()
            pass
        return {'progress': self.progress, 'message': self.message}
    
    def getCompletion(self: Self) -> bool:
        return self.done
    
    def __notifyProgress(self: Self, child: 'ProgressReport'):
        progress = self.getProgress()
        if hasattr(self, 'parent'): self.parent.__notifyProgress(self)
        if hasattr(self, 'taskmanager'):
            self.taskmanager.updateTaskSlotProgress(progress)

    def __str__(self: Self) -> str:
        return f""