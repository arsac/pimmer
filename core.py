#!/usr/bin/python

import os, sys, time, signal, binascii, termcolor, json, subprocess
from time import strftime as date

#sys.path.append( './lib/' )

from config import config

# Here we import the two types of drivers. The event driven driver, and the ticking driver.
import event_driver as eventDriver # For responding to signals
import tick_driver as tickDriver # For constantly sending a type of signal at a certain interval

from itunes_sync import itunesSync 
from module_audio import mpdClient
from web_server import webServer

from interface import *
from logger import PLog


log = PLog(__name__)

#####################################
# GLOBALS
#####################################
DEVPATH           = config.get("ibus","interface_path")
LOGFILE           = config.get("general","log_file")
IBUS              = None
REGISTERED        = False # This is a temporary measure until state driven behaviour is implemented

#####################################
# FUNCTIONS

# Initializes modules as required and opens files for writing
def initialize():
  global IBUS, REGISTERED, DEVPATH
  REGISTERED=False
  
  #mpd = Audio.MpdClient()
  webServer.start()
  
  #mpd.client.listallinfo()
  #print mpdClient.commands()
  #Audio.init()
  #print Audio.client().lsinfo()
  #print Audio.client().commands()
  #print Audio.client().listplaylists()
  mpdClient.init()
  
  
  #print "wtf"
  #sync = ItunesSync()
  #sync.start()
  
  #sys.exit(0)
  
  # Initialize the iBus interface or wait for it to become available.
  while IBUS == None:
    
    #print mpdClient.currentsong()
    
    if os.path.exists(DEVPATH):
      IBUS = ibusFace(DEVPATH)
    else:
      log.warning("USB interface not found at (%s). Waiting 1 seconds.", DEVPATH)
      time.sleep(2)
  
  IBUS.waitClearBus() # Wait for the iBus to clear, then send some initialization signals
  
  eventDriver.init(IBUS)
  tickDriver.init(IBUS)
  
# close the USB device and whatever else is required
def shutdown():
  global IBUS
  
  log.info("Shutting down event driver")
  eventDriver.shutDown()
  
  log.info("Shutting down tick driver")
  tickDriver.shutDown()
  
  log.info("Shutting down mpd client")
  mpdClient.shutDown()
  
  log.info("Shutting down web server")
  webServer.shutDown()
  
  if IBUS:
    log.info("Killing iBUS instance")
    IBUS.close()
    IBUS = None

def run():
  eventDriver.listen()
