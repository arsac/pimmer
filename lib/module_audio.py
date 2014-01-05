#!/usr/bin/python

# The MPD module has practically no documentation as far as I know.. so a lot of this is guess-work, albeit educated guess-work
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

from mpd_lib import MPDResult
from mpd_lib.mpd_client import PimmerMPDClient
from mpd_lib.mpd_elapsed import MPDElapsed
from mpd_lib.mpd_ping import MPDPing
from mpd_lib.mpd_idle import MPDIdle

#####################################
# GLOBALS
#####################################
HOST     = config.get("mpd","host")
PORT     = config.get("mpd","port")
PASSWORD = False
CON_ID   = {'host':HOST, 'port':PORT}
#MUSIC_DIRECTORY = config.get("mpd","music_directory")


CLIENT   = None
PLAYLIST = None
LIBRARY  = None
T_STATUS = None

MPD_STATUS_PLAY = "play"
MPD_STATUS_PAUSE = "pause"
MPD_STATUS_STOP = "stop"

#['add', 'addid', 'channels', 'clear', 'clearerror', 'close', 'commands', 'config', 'consume', 'count', 'crossfade', 'currentsong', 'decoders', 'delete', 'deleteid', 'disableoutput', 'enableoutput', 'find', 'findadd', 'idle', 'kill', 'list', 'listall', 'listallinfo', 'listplaylist', 'listplaylistinfo', 'listplaylists', 'load', 'lsinfo', 'mixrampdb', 'mixrampdelay', 'move', 'moveid', 'next', 'notcommands', 'outputs', 'password', 'pause', 'ping', 'play', 'playid', 'playlist', 'playlistadd', 'playlistclear', 'playlistdelete', 'playlistfind', 'playlistid', 'playlistinfo', 'playlistmove', 'playlistsearch', 'plchanges', 'plchangesposid', 'previous', 'prio', 'prioid', 'random', 'readcomments', 'readmessages', 'rename', 'repeat', 'replay_gain_mode', 'replay_gain_status', 'rescan', 'rm', 'save', 'search', 'searchadd', 'searchaddpl', 'seek', 'seekcur', 'seekid', 'sendmessage', 'setvol', 'shuffle', 'single', 'stats', 'status', 'stop', 'subscribe', 'swap', 'swapid', 'tagtypes', 'toggleoutput', 'unsubscribe', 'update', 'urlhandlers', 'volume']

log = PLog(__name__)



class Status(MPDResult):
  def __str__(self):
    return self.state
  
  
  def get_elapsed(self):
    _elapsed = 0
    if self.elapsed:
      _elapsed = float(self.elapsed)
    return _elapsed
  
  def is_playing(self):
    return self.state == MPD_STATUS_PLAY
  
  def is_paused(self):
    return self.state == MPD_STATUS_PAUSE
  
  def is_stopped(self):
    return self.state == MPD_STATUS_STOP

class Playlist(object):
  tracks = []
  def __init__(self, data):
    self.tracks = []
    for _t in data:
      self.tracks.append(Track(_t))
  
  def json(self):
    _json = {
      "count" : len(self.tracks),
      "tracks" : [],
      
    }
    for _t in self.tracks:
      _json["tracks"].append(_t.json())
    return _json
  
  def __str__(self):
    return self.data
    
class Library(object):
  tracks = []
  def __init__(self, data):
    self.tracks = []
    self.dirs = []
    self.playlists = []
    
    for _t in data:
      if "directory" in _t.keys():
        self.dirs.append(_t["directory"])
      elif "playlist" in _t.keys():
        self.playlists.append(_t["playlist"])
      else:
        self.tracks.append(Track(_t))
  
  def json(self):
    _json = {
      "dirs" : self.dirs,
      "tracks" : []
    }
    if len(self.playlists) > 0:
      _json["playlists"] = self.playlists
    
    for _t in self.tracks:
      _json["tracks"].append(_t.json())
    return _json
  
  def __str__(self):
    return self.data


class Track(MPDResult):
  def __str__(self):
    _artist = self.albumartist or self.artist
    return "%s - %s" % (_artist, self.title)


class PimmerMPDController(object):
  client = None
  is_connected = False
  
  music_directory = None
  playlist_directory = None
  
  idle = None
  
  mpd_data = {}
  
  
  
  mpd_state = None
  
  mpd_currentsong = None
  mpd_playlistinfo = None
  mpd_lsinfo = None
  
  def __init__(self, config = config):
    
    self.music_directory = config.get("mpd","music_directory")
    self.playlist_directory = config.get("mpd","playlist_directory")
    
    #self.connect()
    
  def init(self):
    self.client = PimmerMPDClient()
    
    
    
    log.info('PimmerMPDController ready')
    self.connect()
    self.status()
    self.currentsong()
    self.playlistinfo()
    self.lsinfo()
    
    self.elapsed = MPDElapsed(self.mpd_status.get_elapsed(), not self.mpd_status.is_playing())
    
    self.ping = MPDPing(self.client)
    self.ping.start()
    
    self.idle = MPDIdle(client = self)
    self.idle.start()
    log.info('MPD IDLE started')
    
    
    self.elapsed.start()
    log.info('MPD ELAPSED started')
      
  
  def __getattr__(self, attr):
    
    def client_method(*args, **kwargs):
      _val = None
      #self.client.acquire()
      #if not self.is_connected:
      self.connect()
      
      #self.client.acquire()
      try:
        with self.client:
          _val = getattr(self.client,attr).__call__(*args, **kwargs)
      
      except SocketError, e:
        self.client._reset()
        self.connect()
        print e
        
      #self.client.release()
      
      
      try:
        getattr(self,"setup_%s_data" % attr).__call__(attr, _val)
      except:
        pass
      finally:
        getattr(self,"setup_data").__call__(attr, _val)
      #_setup_f = getattr(self,"setup_%s_data" % attr).__call__(_val)
      
      return _val
    
    log.info('Calling "%s"' % attr)
    
    return client_method
  
  def setup_lsinfo_data(self, attr, value):
    print value
    self.mpd_lsinfo = Library(value)  
  
  def setup_listallinfo_data(self, attr, value):
    self.mpd_listallinfo = Library(value)
  
  def setup_playlistinfo_data(self, attr, value):
    self.mpd_playlistinfo = None
    self.mpd_playlistinfo = Playlist(value)
  
  def setup_deleteid_data(self, attr, value):
    self.playlistinfo()
  
  def setup_currentsong_data(self, attr, value):
    self.mpd_currentsong = Track(value)
  
  def setup_status_data(self, attr, value):
    self.mpd_status = Status(value)
    
  
  
  def setup_data(self, attr, value):
    self.mpd_data[attr] = value
  
  def get_data(self, attr):
    if attr in self.mpd_data.keys():
      return self.mpd_data[attr]
    return
  
  
  def clearload(self, playlist):
    self.clear()
    self.load(playlist)
  
  def add_all(self):
    self.clear()
    self.add('/')
  
  def connect(self):
    if self.is_connected:
      return True
    
    try:
      self.client.connect()
      log.info('Connected to MPD server')
      print "connected"
      self.is_connected = True
    except SocketError:
      log.critical('Could not connect to MPD server')
      self.is_connected = False
    return self.is_connected
  
  def shutDown(self):
    
    self.elapsed.quit()
    self.elapsed.join()
    
    self.ping.quit()
    self.ping.join()
    
    self.idle.quit()
    self.idle.join()
    
    self.close()
    
    log.info('MPD thread shut down')

  def on_player_idle(self):
    #Update current song and status since we received event
    
    self.status()
    
    _elapsed = self.mpd_status.get_elapsed()
    self.elapsed.reset(_elapsed)
    
    if self.mpd_status.is_playing():
      #Mpd is playing and so we should load the new song     
      self.currentsong()
      self.elapsed.resume()
      log.info("%s started playing" % self.mpd_currentsong)
    
    elif self.mpd_status.is_paused():
      log.info("Paused")
      self.elapsed.pause()
      
    elif self.mpd_status.is_stopped():
      log.info("Stopped")
      self.elapsed.pause()
      self.elapsed.reset()
    
    log.info("Song has changed")
    
  def on_update_idle(self):
    log.info("Mpd has triggered an update")
  
  def on_playlist_idle(self):
    self.playlistinfo()
   
  def on_stored_playlist_idle(self):
    self.lsinfo()
    
  def on_options_idle(self):
    self.status()


    

mpdClient = PimmerMPDController()




#mpdIdle = Idle()
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
    log.info('Connected to MPD server')
    #CLIENT.setvol(100)
    PLAYLIST = CLIENT.playlistinfo()
    LIBRARY  = CLIENT.listallinfo()
    
    repeat(True) # Repeat all tracks
  else:
    log.critical('Failed to connect to MPD server')
    log.critical("Sleeping 1 second and retrying")
    time.sleep(1)
    init()

def config():
  if CLIENT:
     return CLIENT.config()


def client():
  return CLIENT

# Updates MPD library
def update():
  log.info('Updating MPD Library')
  CLIENT.update()
  LIBRARY  = CLIENT.listallinfo()

def addAll():
  CLIENT.clear() # Clear current playlist
  CLIENT.add('/') # Add all songs in library (TEMP)
  PLAYLIST = CLIENT.playlistinfo()

def add(path):
  if CLIENT:
    return CLIENT.add(path)

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
      log.warning("MPD lost connection while reading status")
      time.sleep(.5)
    
  if (state['state'] != "stop"):
    if ("songid" in state):
      songID = state['songid']
      if (songID != lastID):
        getTrackInfo()
    if (T_STATUS == None):
      getTrackInfo()
  status = {"status": state, "track": T_STATUS}
  log.debug("Player Status Requested. Returning:")
  log.debug(status)
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
    log.warning("MPD status does not contain songID. Please investigate following status:")
    log.warning(CLIENT.status())
  try:
    currentTID = CLIENT.status()['songid']
    return currentTID
  except e:
    log.warning("Unexpected Exception occured:")
    log.warning(traceback.format_exc())
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
    


def fetchIdle(idle=None):
  if CLIENT:
    return CLIENT.fetch_idle(idle)
    
def sendIdle(idle=None):
  if CLIENT:
    CLIENT.send_idle(idle)
    
def noIdle():
  if CLIENT:
    try:
      CLIENT.noidle()
    except:
      pass