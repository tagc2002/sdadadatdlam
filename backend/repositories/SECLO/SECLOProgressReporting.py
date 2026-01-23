import logging
from threading import Lock
from typing import List, Self, Dict, Tuple

logger = logging.getLogger(__name__)
class ProgressReport():
    #TODO composable behavior
    def __init__(self, isComposable:bool = False):
        self.progress = 0.0
        self.steps = 0
        self.message = ''
        self.checked = Lock()
        self.done = False
        self.subprogresses: List[Tuple['ProgressReport', str]] = []


    def setSteps(self: Self, steps: int) -> Self:
        logger.debug(f'SET STEPS {steps}')
        self.steps = steps
        self.done = False
        return self
    
    def compose(self: Self, subprogress: 'ProgressReport', message: str = "") -> Self:
        logger.debug(f"COMPOSE {f'({message})' if message else ''}")
        self.subprogresses.append((subprogress, message))
        return self
    
    def setProgress(self, step: float, message) -> Self:
        if (len(self.subprogresses)) > 0:
            raise AttributeError("Can't set progress on a composed report")
        self.progress = step / self.steps
        self.message = message
        self.done = False
        if self.checked.locked():
            self.checked.release() 
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
        logger.debug(f'INCREASE PROGRESS: {self.progress} {f'({message})' if message else ''}')
        return self        
    
    def setMessage(self: Self, message: str) -> Self:
        logger.debug(f'SET MESSAGE: {message}')
        self.message = message
        if self.checked.locked():
            self.checked.release()
        return self
    
    def setCompletion(self: Self, message: str) -> Self:
        logger.debug(f'SET COMPLETION {f'({message})' if message else ''}')
        self.progress = 1
        self.done = True
        self.message = message
        if self.checked.locked():
            self.checked.release()  
        return self

    def getProgress(self: Self) -> Dict:
        logger.debug("GET PROGRESS")
        if self.subprogresses:
            self.progress = 0
            for (progress, message) in self.subprogresses:  
                if progress.getCompletion():
                    self.progress += 1/len(self.subprogresses)
                else:
                    currentProgress = progress.getProgress()  
                    self.progress = currentProgress['progress']
                    self.message = message + ": " + currentProgress['message']
                    break
            else:
                self.message = self.subprogresses[-1][1] + ": " + self.subprogresses[-1][0].message
                self.done = True
        else:
            self.checked.acquire()
        return {'progress': self.progress, 'message': self.message}
    
    def getCompletion(self: Self) -> bool:
        logger.debug("GET COMPLETION")
        return self.done
