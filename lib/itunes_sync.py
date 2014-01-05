import paramiko
import time
import os
import StringIO
import plistlib
import tempfile
import sys
import uuid
import threading
import Queue
import urllib
import md5
import logging
from multiprocessing import Process
from module_audio import mpdClient


from HTMLParser import HTMLParser
from urlparse import urlparse
from datetime import datetime
import module_display
from config import config
from logger import PLog

log = PLog(__name__)


logging.getLogger("paramiko").setLevel(logging.WARNING) 

ITUNES_REMOTE_XML_PATH = config.get("itunes_sync","itunes_remote_xml_path")


MPD_SYNC_DIR = "itunes"

MPD_PLAYLIST_DIR = config.get("mpd","playlist_directory")
MPD_MUSIC_DIR = config.get("mpd","music_directory")

TMP_FOLDER = "/tmp/%s" % MPD_SYNC_DIR

PLAYLISTS = config.getlist("itunes_sync","itunes_playlists")

PLAYLIST_DATA = {}

DOWNLOADERS = 3

#"|".join(PLAYLISTS)

GET_SONG_IDS_CMD = """awk '/^\t\<key\>Playlists\<\/key\>/,/^\t\<\/array\>/' '%s' \
| awk '/^\t{3}\<key\>Name\<\/key\>\<string\>%s\<\/string\>/,/^\t{2}\<\/dict\>/' \
| grep -oE '<key>Track ID</key><integer>(.*)</integer>|<key>Name</key><string>(.*)</string>' \
| sed -e 's/<key>Track ID<\/key><integer>//g' -e 's/<\/integer>//g' \
| sed -e 's/<key>Name<\/key><string>//g' -e 's/<\/string>//g' \
| tr -d '\t'""" % (ITUNES_REMOTE_XML_PATH, "|".join(PLAYLISTS))


GET_SONG_IDS_SOURCE = """awk '/^\t\<key\>Tracks\<\/key\>/,/^\t\<\/array\>/' '%s' \
| awk '/^\t{3}\<key\>Track ID\<\/key\>\<integer\>(%s)\<\/integer\>/,/^\t{2}\<\/dict\>/' \
| grep -E '<key>Location</key><string>file://localhost' \
| sed -e 's/<key>Location<\/key><string>//g' -e 's/<\/string>//g' \
| tr -d '\t'""" % (ITUNES_REMOTE_XML_PATH, "%s")


# Close

def get_playlist_file(playlist):
  global MPD_PLAYLIST_DIR
  
  return "%s/%s.m3u" % (MPD_PLAYLIST_DIR, playlist)  


def open_playlist_file(playlist):
  playlist_filename = get_playlist_file(playlist)
  playlist_file = open(playlist_filename, "w")
  
  return playlist_file

#def getPlaylistCmd(playlist):
#  return GET_SONG_IDS_CMD % (playlist)
def libraryBasedir():
  global MPD_MUSIC_DIR
  return MPD_MUSIC_DIR  

def getExistingFiles():
  os.chdir(localPath())
  existing_files = []
  for track in os.listdir("."):
    existing_files.append(track)
  return existing_files

def tmpFilename(filename):
  return "%s/%s" % (TMP_FOLDER, filename)


def localPath(filename = None):
  global  MPD_SYNC_DIR
  _path = "%s/%s" % (libraryBasedir(), MPD_SYNC_DIR)
  if filename:
    _path = "%s/%s" % (_path, filename)
  return _path

def getFilenames(filename):
  remote_path, remote_filename = os.path.split(filename)
  m = md5.new()
  m.update(remote_path)
  filename, ext = os.path.splitext(remote_filename)
  local_filename = "%s_%s%s" % (filename, m.hexdigest(),ext)
  local_path = localPath()
  return local_filename, local_path, remote_filename, remote_path


def isPlaylist(playlist):
  return playlist in PLAYLISTS


def setupPlaylists():
  PLAYLIST_DATA = {}
  for playlist in PLAYLISTS:
    PLAYLIST_DATA[playlist] = {}

def downloadStatusDisplay(track_count,total_count):
  _current_track = total_count - track_count
  _percent = int(( _current_track / float(total_count) ) * 100)
  _percent_display = "%d%%" % _percent
  _progress_bar_length = module_display.MAX_STRINGLEN - 6
  
  _progress_bar_status = int(_progress_bar_length * ( _percent / float(100)))
  
  _s = "|"
  for i in range(_progress_bar_length):
  
    if i < _progress_bar_status:
      _s += "="
    else:
      _s += " "
  
  _s += "|%s" % _percent_display
  return _s



class ItunesSync:
  running = False
  
  def __init__(self):
    self.__process = None
    self.__ssh = paramiko.SSHClient()
    self.__ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #print "init"
  def start(self):
    if self.is_running():
      log.info("Itunes Sync is already running")
      return False
    
    self.__process = Process(target=self.run)
    self.__process.start()
    #self.run()
    return True
    #self.__process = Process(target=self.run)
    #self.__process.start()
  def status(self):
    return self.is_running()
  
  def is_running(self):
    return self.__process != None and self.__process.is_alive()
  
  def run(self):
    self.running = True
    log.warning("test")
    log.info("iTunes Sync Started")
    
    startTime = datetime.now()
    
    #ssh = paramiko.SSHClient()
    
    
    #get config items
    ssh_host = config.get("ssh","host")
    ssh_port = config.get("ssh","port")
    
    if ssh_port:
      ssh_port = int(ssh_port) if ssh_port else None
    
    ssh_user = config.get("ssh","user")
    ssh_keyfile = config.get("ssh","key_filename")
    
    
    self.__ssh.connect(ssh_host, port=ssh_port, username=ssh_user, key_filename = ssh_keyfile)
    
    playlists = {}
    cur_playlist = None
    
    dl_queue = SyncQueue()
    dont_del_queue = SyncQueue()
    
    #for playlist in PLAYLISTS:
    stdin, stdout, stderr = self.__ssh.exec_command(GET_SONG_IDS_CMD)
    ids = stdout.readlines()
    for track_id in ids:
      track_id = track_id.rstrip()
      if isPlaylist(track_id):
        cur_playlist = track_id
        continue
        
      if(cur_playlist):
        if cur_playlist not in playlists:
          playlists[cur_playlist] = []
        playlists[cur_playlist].append(track_id)
    
    htmlParse = HTMLParser()
    
    for playlist in playlists.keys():
      tracks = playlists[playlist]
      stdin, stdout, stderr = self.__ssh.exec_command(GET_SONG_IDS_SOURCE % "|".join(tracks))
      playlist_tracks = stdout.readlines()
      tracks = []
      for track in playlist_tracks:
        track = track.rstrip()
        track = urlparse(track, allow_fragments=False).path
        track = urllib.url2pathname(track)
        track = urllib.unquote_plus(track)
        track =  htmlParse.unescape(track)
        track = track.decode('utf-8')
        
        if track not in dl_queue:
          dl_queue.put(track)
        
        _track_paths = getFilenames(track)
        track = "%s/%s" % (MPD_SYNC_DIR,_track_paths[0])
        print track
        tracks.append(track)
        
        
      playlists[playlist] = tracks
     

    #Check if the tmp folder exists
    if not os.path.exists(TMP_FOLDER):
    	os.makedirs(TMP_FOLDER)
    
    #Check if the final folder exists
    if not os.path.exists(localPath()):
    	os.makedirs(localPath())
    

    existing_tracks = getExistingFiles()
    
    dl_queue_size = dl_queue.qsize()
    
    for i in range(DOWNLOADERS):
      Downloader(dl_queue, dl_queue_size, dont_del_queue, self.__ssh).start()
     
    dl_queue.join()
    
    while not dont_del_queue.empty():
      track = dont_del_queue.get()
      
      if track in existing_tracks:
        existing_tracks.remove(track)
      
      dont_del_queue.task_done()
      #print track
      
    
    for orphan_track in existing_tracks:
       #try:
       if orphan_track:
         os.remove(localPath(orphan_track))
       #print localPath(orphan_track)
       
    log.info("Songs Copied")
    #Audio.addAll()
     
    #mpdClient.update()
    
    #ssh_host = config.get("ssh","host")
    for playlist in playlists.keys():
      _tracks = playlists[playlist]
      
      playlist_file = open_playlist_file(playlist)
      print playlist_file
      
      for _t in _tracks:
        playlist_file.write('%s\n' % _t)
      
      playlist_file.close()
      
    mpdClient.update()
    mpdClient.add_all()
      #Audio.client()
      #mpdClient.clear()
      #try:
      #  mpdClient.rm(playlist)
      #except:
      #  pass
      
      #for _t in _tracks:
      #  mpdClient.addid(_t)
      #mpdClient.save(playlist)
      
      #mpdClient.listplaylists()
      
      #print mpdClient.listplaylists()
    
    #print stdout.readlines()
    #sftp.close()
    self.__ssh.close()
    log.info("Suyc completed in %s" % (datetime.now()-startTime))
    self.running = False
    #print playlists
    #sftp.put(REMOTE_SCRIPT, REMOTE_SCRIPT_PATH)
    #st_uid = sftp.stat(REMOTE_SCRIPT_PATH)
class SyncQueue(Queue.Queue):
    def __contains__(self, item):
        with self.mutex:
            return item in self.queue
            
class Downloader(threading.Thread):

    def __init__(self, queue, size, dont_del_queue, ssh):
        self.__queue = queue
        self.__sftp = ssh.open_sftp()
        self.__size = size
        self.__dont_del_queue = dont_del_queue
        threading.Thread.__init__(self)

    def run(self):
        while not self.__queue.empty():
          
          try:
            item = self.__queue.get()
            
            #display current status on lcd
            downloadStatusDisplay(self.__queue.qsize(), self.__size)
            
            local_filename, local_path, remote_filename, remote_path = getFilenames(item)
            
            tmp_filename = tmpFilename(local_filename)
            
            remote_size = self.__sftp.lstat(item).st_size
            
            try:
              
              local_size = os.stat(localPath(local_filename)).st_size
              if local_size != remote_size:
                log.info("the size for %s differs from remote" % local_filename)
                raise OSError
              
              log.info("%s exists already" % local_filename)
              pass
            
            except OSError:
              log.info("%s does not exist and will be copied" % local_filename)
              
              #check if file is already downloaded to tmp directory
              try:
                
                local_tmp_size = os.stat(tmp_filename).st_size
                if local_tmp_size == remote_size:
                  log.info("%s tmp file already exists" % local_filename)
                else:
                  log.info("%s tmp file does not exist and will be downloaded remotely" % local_filename)
                  raise OSError
              
              except OSError:
           	  
                try:              
                  
                  self.__sftp.get(item, tmp_filename)
                  
                except IOError:
                  log.debug("could not download %s" % item)
                  break
              finally:
                #move tmp file
                #print localPath(local_filename)
                #log.debug("could not download %s" % localPath(local_filename))
                try:
                  os.rename(tmp_filename,localPath(local_filename))
                  log.debug("renammed %s" % localPath(local_filename))
                except OSError:
                  log.debug("could not rename %s" % localPath(local_filename))
                  pass
            
          except Queue.Empty:
            break
          finally:
          	#current_size = self.__queue.qsize()
            #print "%d/%d" % ((self.__size - current_size) + 1, self.__size)
            
            
            self.__dont_del_queue.put(local_filename)
            self.__queue.task_done()
            
    
    
    #print st_uid
    
    #xml_file = tempfile.TemporaryFile()
    
    #sftp.get(ITUNES_XML_PATH,xml_file.name, callback=callback)
    
    #xml_library = plistlib.readPlist(xml_file)
    
    #print xml_file
itunesSync = ItunesSync()
