import web, os, sys, subprocess, commands, mimetypes, re
import json as JSON
import module_audio as pB_audio
import threading
import posixpath
import urllib

def enum(**enums):
  return type('Enum', (), enums)

currentTrackID = -1

urls = (
  '/', 'index',
  '/sync', 'sync',
  '/update', 'update',
  '/get_library', 'getLibrary',
  '/get_playlist', 'getPlaylist',
  '/getInfoPath', 'getInfoPath',
  '/playlistMod', 'playlistMod',
  '/status', 'status'
)

root_path = os.path.join(os.path.dirname( __file__ ), '..')

template_path = "%s/templates/" % root_path
static_path = "%s/static/" % root_path
#print template_path

render = web.template.render(template_path)
PYBUS_SOCKET_FILE = "/tmp/ibus_custom.log"

#GLOBALS

HTTP_PORT = 3333


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
class index:
  def GET(self):
    #pB_audio.init()
    return render.index()

class sync:
  def GET(self):
    return "sync"
  

class musicStatus:
  def GET(self):
    global currentTrackID
    status = pB_audio.getInfo(currentTrackID)
    status['custom'] = getCustomData()
    if ('songid' in status['status'].keys()):
      currentTrackID = status['status']['songid']
    return JSON.dumps(status)

class getLibrary:
  def GET(self):
    library = pB_audio.getLibrary()
    return JSON.dumps(library)

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
  web.config.debug = False
  app = WebApplication(urls, globals())
  wsgifunc = app.wsgifunc()
  wsgifunc = StaticMiddleware(wsgifunc)
  wsgifunc = web.httpserver.LogMiddleware(wsgifunc)
  server = web.httpserver.WSGIServer(("0.0.0.0", HTTP_PORT), wsgifunc)
  print "http://%s:%d/" % ("0.0.0.0", HTTP_PORT)

  return server



class WebApplication(web.application):
    def run(self, port=HTTP_PORT, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('0.0.0.0', port))
        
class StaticMiddleware:
    """WSGI middleware for serving static files."""
    def __init__(self, app, prefix='/static/', root_path=static_path):
        self.app = app
        self.prefix = prefix
        self.root_path = root_path

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        path = self.normpath(path)
        
        if path.startswith(self.prefix):
            environ["PATH_INFO"] = os.path.join(self.root_path, web.lstrips(path, self.prefix))
            
            return web.httpserver.StaticApp(environ, start_response)
        else:
            return self.app(environ, start_response)

    def normpath(self, path):
        path2 = posixpath.normpath(urllib.unquote(path))
        if path.endswith("/"):
            path2 += "/"
        return path2
        
        
