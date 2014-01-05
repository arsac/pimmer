from threading import Lock, Thread
import threading
import json

class MPDResult(object):
  data = {}
  def __init__(self, data):
    self.data = data
    for k in data.keys():
      setattr(self, k, data[k])
  
  def json(self):
    return self.data
  
  def __getattr__(self, attr):
    return None

class MPDThread(threading.Thread):

    abort = False
    running = False
    
    def __init__(self):
        threading.Thread.__init__(self)
        
    
    def isRunning(self):
        return self.running

    def quit(self):
        self.abort = True

    def canShutdown(self):
        return (self.abort and not self.running)