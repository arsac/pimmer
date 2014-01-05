import web, os, sys, subprocess, commands, mimetypes, re
import json as JSON
import threading
import posixpath
import urllib
from itunes_sync import itunesSync
from module_audio import mpdClient
from logger import PLog

log = PLog(__name__)


def enum(**enums):
  return type('Enum', (), enums)

currentTrackID = -1

urls = (
  '/', 'index',
  '/sync', 'sync',
  '/update', 'update',
  '/action/(.+)', 'action',
  '/library', 'library',
  '/get_playlist', 'getPlaylist',
  '/getInfoPath', 'getInfoPath',
  '/playlistMod', 'playlistMod',
  '/status', 'status'
)


root_path = os.path.join(os.path.dirname( __file__ ), '..')

#root_path = ""

template_path = "%s/templates/" % root_path
static_path = "%s/static/" % root_path
#print template_path


render = web.template.render(template_path)
PYBUS_SOCKET_FILE = "/tmp/ibus_custom.log"

#GLOBALS

HTTP_PORT = 8080


#########################
# Internal Functions
######################### 
def getCustomData():
  status = None
  if (os.path.isfile(PYBUS_SOCKET_FILE)):  
    log_file = open(PYBUS_SOCKET_FILE,"r")
    log_file_data = log_file.read()
    log_file.close() 
    try:
      status = JSON.loads(log_file_data)
    except Exception, e:
      print "Error loading custom data file"
      print e
  return(status)

#########################
# Web stuff
#########################

def statusJson():
	return {
	  "sync" : itunesSync.status(),
	  "elapsed": mpdClient.elapsed.elapsed,
      "currentsong": mpdClient.mpd_currentsong.json(),
      "playlist": mpdClient.mpd_playlistinfo.json(),
      "status": mpdClient.mpd_status.json(),
      "playlists": mpdClient.mpd_lsinfo.json()
    }



class index:
  def GET(self):
    #pB_audio.init()
    return render.index()

class sync:
  def GET(self):
    web.header('Content-Type', 'application/json')
    _sync = itunesSync.start()
    result = {
      "sync" : itunesSync.status()
    }
    return JSON.dumps(result)

class action:
  def GET(self, action = None):
    web.header('Content-Type', 'application/json')
    data = web.input(_method='get')
    
    _params = None

    try:
      _params = data.params.split(",")
    except:
      pass

    args = []
    
    if _params:
      for i in _params:
        if i in data.keys():
          args.append(data[i])
    
    
    if action:
      result = False
     
      try:
        _f = getattr(mpdClient, action)
        _r = _f(*args)
        result = statusJson()
        result["action"] = _r
        
      except AttributeError:
        log.info("Action %s not available", action)
    return JSON.dumps(result)
  

class status:
  def GET(self):
    web.header('Content-Type', 'application/json')
    result = statusJson()
    return JSON.dumps(result)

class library:
  def GET(self):
    web.header('Content-Type', 'application/json')
    mpdClient.listallinfo()
    _result = {
      "library" : mpdClient.mpd_listallinfo.json()
    }
    return JSON.dumps(_result)

class getPlaylist:
  def GET(self):
    playlist = pB_audio.getPlaylist()
    return JSON.dumps(playlist)

class getInfoPath:
  def GET(self):
    getData = web.input(_method='get')
    path = getData.path
    return JSON.dumps(playlist)
    
class playlistMod:
  def GET(self):
    getData = web.input(_method='get')
    if (getData.type == "add"):
      filePath = getData.path
      pB_audio.addSong(filePath)
      
    if (getData.type == "play"):
      filePath = getData.path
      pB_audio.playSong(filePath)

    if (getData.type == "remove"):
      filePath = getData.path
      pB_audio.removeSong(filePath)

    if (getData.type == "pause"):
      status = pB_audio.getInfo(currentTrackID)
      if status['status']['state'] == "stop":
        pB_audio.play()  
      else:
        pB_audio.pause()
    if (getData.type == "next"):
      pB_audio.next()
    if (getData.type == "previous"):
      pB_audio.previous()
    

def init():
  #pB_audio.init()
  #web.config.debug = False
  #app = WebApplication(urls, globals())
  #wsgifunc = app.wsgifunc()
  #wsgifunc = StaticMiddleware(wsgifunc)
  #wsgifunc = web.httpserver.LogMiddleware(wsgifunc)
  #server = web.httpserver.WSGIServer(("0.0.0.0", HTTP_PORT), wsgifunc)
  print "http://%s:%d/" % ("0.0.0.0", HTTP_PORT)
  app = web.application(urls, globals())
  return app
