from threading import Lock

mutex = Lock()

class ProgressReport():
    def __init__(self, steps, message):
        self.progress = 0.0
        self.steps = steps
        self.message = message
        self.checked = False

    def setProgress(self, step, message):
        with mutex:
            self.progress = step / self.steps
            self.message = message
            self.checked = False
    
    def getProgress(self):
        with mutex:
            if (self.checked):
                return None
            self.checked = True
            return {'progress': self.progress, 'message': self.message}