#!/usr/bin/python

# The MPD module has practically no documentation as far as I know.. so a lot of this is guess-work, albeit educated guess-work
import pprint, os, sys, time, signal, logging
from mpd import (MPDClient, CommandError)
from socket import error as SocketError
import core

#####################################
# GLOBALS
#####################################
HOST     = 'localhost'
PORT     = '6600'
PASSWORD = False
CON_ID   = {'host':HOST, 'port':PORT}
VOLUME   = 90

CLIENT   = None
PLAYLIST = None
LIBRARY  = None
T_STATUS = None

#####################################
# FUNCTIONS
#####################################
def mpdConnect(client, con_id):
  try:
    client.connect(**con_id)
  except SocketError:
    return False
  return True

def init():
  global CLIENT, PLAYLIST, LIBRARY
  ## MPD object instance
  CLIENT = MPDClient()
  if mpdConnect(CLIENT, CON_ID):
    logging.info('Connected to MPD server')
    #CLIENT.setvol(100)
    PLAYLIST = CLIENT.playlistinfo()
    LIBRARY  = CLIENT.listallinfo()
    
    repeat(True) # Repeat all tracks
  else:
    logging.critical('Failed to connect to MPD server')
    logging.critical("Sleeping 1 second and retrying")
    time.sleep(1)
    init()

def client():
  return CLIENT

# Updates MPD library
def update():
  logging.info('Updating MPD Library')
  CLIENT.update()
  LIBRARY  = CLIENT.listallinfo()

def addAll():
  CLIENT.clear() # Clear current playlist
  CLIENT.add('/') # Add all songs in library (TEMP)
  PLAYLIST = CLIENT.playlistinfo()
    
def quit():
  if CLIENT:
    CLIENT.disconnect()

def play():
  CLIENT.play()

def stop():
  if CLIENT:
    CLIENT.stop()

def pause():
  CLIENT.pause()

def next():
  CLIENT.next()

def previous():
  CLIENT.previous()

def repeat(repeat, toggle=False):
  if toggle:
    current = int(CLIENT.status()['repeat'])
    repeat = (not current) # Love this
  CLIENT.repeat(int(repeat))
  return repeat

def random(random, toggle=False):
  if toggle:
    current = int(CLIENT.status()['random'])
    random = (not current) # Love this
  CLIENT.random(int(random))
  return random

def seek(delta):
  seekDest = int(float(CLIENT.status()['elapsed']) + delta)
  playListID = int(CLIENT.status()['song'])
  CLIENT.seek(playListID, seekDest)

def getTrackInfo():
  global T_STATUS
  currentTID = getTrackID()
  for song in PLAYLIST:
    trackID = song["id"]
    if trackID == currentTID:
      T_STATUS = song

def getInfo(lastID=-1):
  if CLIENT == None:
    init()
  state = None
  while not state:
    try:
      state = CLIENT.status()
    except Exception, e:
      logging.warning("MPD lost connection while reading status")
      time.sleep(.5)
    
  if (state['state'] != "stop"):
    if ("songid" in state):
      songID = state['songid']
      if (songID != lastID):
        getTrackInfo()
    if (T_STATUS == None):
      getTrackInfo()
  status = {"status": state, "track": T_STATUS}
  logging.debug("Player Status Requested. Returning:")
  logging.debug(status)
  return status
  
def isStopped():
  return getInfo()["status"]["state"] == "stop"

def getElapsed():
  _elapsed = 0
  if CLIENT:
    _status = status()
    if _status["elapsed"]:
      _elapsed = _status["elapsed"]
    
  return float(_elapsed)


def getInfoByPath(filePath):
  for song in PLAYLIST:
   path = song["file"]
   if path == filePath:
     return song

def addSong(filepath):
  global PLAYLIST
  if (getInfoByPath(filepath) == None):
    CLIENT.add(filepath)
    PLAYLIST = CLIENT.playlistinfo()

def removeSong(filepath):
  global PLAYLIST
  song = getInfoByPath(filepath)
  CLIENT.deleteid(song['id'])
  PLAYLIST = CLIENT.playlistinfo()

def playSong(filepath):
  song = getInfoByPath(filepath)
  CLIENT.playid(song['id'])

def getPlaylist():
  return PLAYLIST

def getLibrary():
  return LIBRARY

def  getTrackID():
  if ("songid" not in CLIENT.status()):
    logging.warning("MPD status does not contain songID. Please investigate following status:")
    logging.warning(CLIENT.status())
  try:
    currentTID = CLIENT.status()['songid']
    return currentTID
  except e:
    logging.warning("Unexpected Exception occured:")
    logging.warning(traceback.format_exc())
    return 0

def status():
  if CLIENT:
    return CLIENT.status()

def currentsong():
  if CLIENT:
    return CLIENT.currentsong()
    
    
def getTrackArtist(track = None):
  return getTrackItem("artist",track)

def getTrackAlbum(track = None):
  return getTrackItem("album",track)
  
def getTrackTitle(track = None):
  return getTrackItem("title",track)

def getTrackItem(key,track = None):
  if track == None:
    track = currentsong()
  if key in track:
    return track[key]
    
    

def fetchIdle():
  if CLIENT:
    return CLIENT.fetch_idle()
    
def sendIdle():
  if CLIENT:
    CLIENT.send_idle()
    
def noIdle():
  if CLIENT:
    try:
      CLIENT.noidle()
    except:
      pass