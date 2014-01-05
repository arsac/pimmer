import pprint, os, sys, time, signal

from socket import error as SocketError

from config import config
from logger import PLog

import threading

from mpd_lib import MPDThread

from mpd import (MPDClient, ConnectionError, CommandError, PendingCommandError)

from mpd_lib.mpd_client import PimmerMPDClient


log = PLog(__name__)


class MPDIdle(MPDThread):
    last_idle = None
    last_idle_time = time.time()
    
    def __init__(self, client = None, idle = None):
      
      self.__idle = idle
      self.__client = client
      #self.__conn = self.__client.client
      self.__conn = PimmerMPDClient()
      
      MPDThread.__init__(self)
    
    def quit(self):
      log.info("Shutting down Mpd Idle")
      MPDThread.quit(self)
      
      try:
        self.__conn.noidle()
      except CommandError:
        pass
      
      self.__conn.close()
      try:
        self.__conn.disconnect()
      except ConnectionError:
        pass
        
      
    
    
    
    def send_idle(self):
      with self.__client.client:
        self.__conn.send_idle(self.__idle)
      log.info("Mpd Idle sent for %s", (self.__idle))
    
    def fetch_idle(self):
      #with self.__conn:
      _item = self.__conn.fetch_idle(self.__idle)
      log.info("Mpd Idle fetched for %s", (self.__idle))
      return _item
    
    def run(self):
        if self.__conn.connect():
          log.info("Mpd Idle Connected")
        
        self.send_idle()
        
        wait = 1
        while True and not self.abort:
            try:
               
               events = self.fetch_idle()
               
               for event in events:
                 log.info("Mpd Idle Called %s", event)
                 try:
                   getattr(self.__client, "on_%s_idle" % event).__call__()
                 except AttributeError:
                   log.info("No idle method for %s", event)
                   pass

               
            except PendingCommandError:
               time.sleep(wait)
               self.send_idle()
            except ConnectionError:
               if not self.abort:
                  self.__conn.connect()
               time.sleep(wait)
               pass
            
            




