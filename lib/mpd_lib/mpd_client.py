import pprint, os, sys, time, signal
import logging
from socket import error as SocketError
import core
from config import config
from logger import PLog
import mpd
from threading import Lock, Thread
import threading



from mpd import (MPDClient, ConnectionError, CommandError, PendingCommandError)


log = PLog(__name__)


class PimmerMPDClient(MPDClient):
  config = config
  is_connected = False
  
  def __init__(self, use_unicode=False):
    
    
    self.__host = self.config.get("mpd","host")
    self.__port = self.config.get("mpd","port")
    self.__timeout = 10
    #MPDClient.__init__(self, *a, **k)
    MPDClient.__init__(self,use_unicode = use_unicode)
    self.use_unicode = use_unicode
    self._lock = Lock()
  
  def connect(self, timeout=None):
    try:
      MPDClient.connect(self, host = self.__host, port = self.__port, timeout = self.__timeout)
      self.is_connected = True
    except SocketError:
      log.critical('Could not connect to MPD server')
      self.is_connected = False
    return self.is_connected
  
  def acquire(self):
      #log.info("aquiring lock")
      self._lock.acquire()
  def release(self):
      #log.info("releasing lock")
      self._lock.release()
  def __enter__(self):
      self.acquire()
  def __exit__(self, type, value, traceback):
      self.release()