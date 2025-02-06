from threading import Lock

mutex = Lock()

class ProgressReport():
    def __init__(self):
        self.progress = 0.0
        self.steps = 0
        self.message = ''
        self.checked = Lock()
        self.done = False

    def setSteps(self, steps):
        with mutex:
            self.steps = steps
            self.done = False
    
    def setProgress(self, step: float, message):
            self.progress = step / self.steps
            self.message = message
            self.done = False
            if self.checked.locked():
                self.checked.release()  

    def increaseProgress(self, step:int , message: str | None = None):
        with mutex:
            self.progress += 1/self.steps
            if message != None:
                self.message = message
            self.done = False
            if self.checked.locked():
                self.checked.release()            
    
    def setMessage(self, message):
        with mutex:
            self.message = message
            if self.checked.locked():
                self.checked.release()
    
    def setCompletion(self, message):
        with mutex:
            self.progress = 1
            self.done = True
            self.message = message
            if self.checked.locked():
                self.checked.release()  

    def getProgress(self):
        self.checked.acquire()
        with mutex:
            return {'progress': self.progress, 'message': self.message}
    
    def getCompletion(self):
        with mutex:
            return self.done