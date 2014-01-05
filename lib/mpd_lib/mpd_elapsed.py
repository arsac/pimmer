import pprint, os, sys, time, signal
import logging
from socket import error as SocketError
import core
from config import config
from logger import PLog
import mpd
from threading import Lock, Thread
import threading



from mpd_lib import MPDThread

log = PLog(__name__)

class MPDElapsed(MPDThread):
    elapsed = 0
    paused = False
    
    def __init__(self, elapsed = 0, paused = False):
      self.paused = paused
      self.elapsed = elapsed
      MPDThread.__init__(self)
        
    def run(self):
      import time
      
      while True and not self.abort:
        if self.paused:
           time.sleep(.1)
        else:
          time.sleep(1)
          self.elapsed += 1
        
        if not self.paused:
          self.display()
    
    def reset(self,elapsed=0):
       self.elapsed = elapsed
    
    def status(self):
       return self.elapsed
       
    def pause(self):
       self.paused = True
    
    def resume(self):
	   self.paused = False
    
    def display(self):
      m, s = divmod(self.elapsed, 60)
      _d = "%02d:%02d" % (m, s)
      log.info(_d)
      return _d
      
        
