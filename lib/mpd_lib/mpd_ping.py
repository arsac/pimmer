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
PING_SLEEP = 5


class MPDPing(MPDThread):
    
    def __init__(self, client):
      self.__client = client
      
      MPDThread.__init__(self)
        
    def run(self):
      import time
      
      while True and not self.abort:
        with self.__client:
          self.__client.ping()
        time.sleep(PING_SLEEP)
        
    def quit(self):
      self.__client = None
      MPDThread.quit(self)