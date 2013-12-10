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

from HTMLParser import HTMLParser
from urlparse import urlparse
import module_audio as Audio


#paramiko.util.log_to_file('/tmp/paramiko.log')

# Open a transport

SSH_HOST = "192.168.1.10"
SSH_PORT = 22
SSH_USER = "mailoarsac"
SSH_KEYFILE = ".ssh/id_rsa"

ITUNES_XML_PATH = "/Users/mailoarsac/Music/iTunes/iTunes Music Library.xml"

MPD_BASEDIR = None
MPD_SYNC_DIR = "itunes"

TMP_FOLDER = "/tmp/%s" % MPD_SYNC_DIR

PLAYLISTS = ["Top 25 Most Played"]

PLAYLIST_DATA = {}

DOWNLOADERS = 3

#"|".join(PLAYLISTS)

GET_SONG_IDS_CMD = """awk '/^\t\<key\>Playlists\<\/key\>/,/^\t\<\/array\>/' '%s' \
| awk '/^\t{3}\<key\>Name\<\/key\>\<string\>%s\<\/string\>/,/^\t{2}\<\/dict\>/' \
| grep -oE '<key>Track ID</key><integer>(.*)</integer>|<key>Name</key><string>(.*)</string>' \
| sed -e 's/<key>Track ID<\/key><integer>//g' -e 's/<\/integer>//g' \
| sed -e 's/<key>Name<\/key><string>//g' -e 's/<\/string>//g' \
| tr -d '\t'""" % (ITUNES_XML_PATH, "|".join(PLAYLISTS))


GET_SONG_IDS_SOURCE = """awk '/^\t\<key\>Tracks\<\/key\>/,/^\t\<\/array\>/' '%s' \
| awk '/^\t{3}\<key\>Track ID\<\/key\>\<integer\>(%s)\<\/integer\>/,/^\t{2}\<\/dict\>/' \
| grep -E '<key>Location</key><string>file://localhost' \
| sed -e 's/<key>Location<\/key><string>//g' -e 's/<\/string>//g' \
| tr -d '\t'""" % (ITUNES_XML_PATH, "%s")




#print sftp
# Download

#filepath = '/etc/passwd'
#localpath = '/home/remotepasswd'
#sftp.get(filepath, localpath)

# Upload

#filepath = '/home/foo.jpg'
#localpath = '/home/pony.jpg'
#sftp.put(filepath, localpath)

# Close

#def getPlaylistCmd(playlist):
#  return GET_SONG_IDS_CMD % (playlist)
def libraryBasedir():
  global MPD_BASEDIR
  if not MPD_BASEDIR:
    MPD_BASEDIR = Audio.config()
  return MPD_BASEDIR  

def getExistingFiles():
  os.chdir(libraryBasedir())
  for files in os.listdir("."):
    print files

def tmpFilename(filename):
  return "%s/%s" % (TMP_FOLDER, filename)


def localPath():
  return "%s/%s" % (libraryBasedir(), MPD_SYNC_DIR)

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



def callback(data, total):
  print data
  print total

class Sync:
  
  transport = None
  
  def __init__(self):
    #self.transport = paramiko.Transport((SSH_HOST, SSH_PORT))
    print "init"
    
  def run(self):
    #self.transport.connect(username = SSH_USER)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    #keyfile = paramiko.RSAKey.from_private_key_file(StringIO.StringIO(open(SSH_KEYFILE, 'r').read()))
    
    ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, key_filename = SSH_KEYFILE)
    #sftp = ssh.open_sftp()
    playlists = {}
    cur_playlist = None
    
    dl_queue = DownloadQueue()
    #for playlist in PLAYLISTS:
    stdin, stdout, stderr = ssh.exec_command(GET_SONG_IDS_CMD)
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
      stdin, stdout, stderr = ssh.exec_command(GET_SONG_IDS_SOURCE % "|".join(tracks))
      playlist_tracks = stdout.readlines()
      tracks = []
      for track in playlist_tracks:
        track = track.rstrip()
        track = urlparse(track, allow_fragments=False).path
        track = urllib.url2pathname(track)
        track = urllib.unquote_plus(track)
        track =  htmlParse.unescape(track)
        track = track.decode('utf-8')
        tracks.append(track)
        if track not in dl_queue:
          dl_queue.put(track)
        
      playlists[playlist] = tracks
     
    
    existing_files = getExistingFiles()
    
    print existing_files
    
    if not os.path.exists(TMP_FOLDER):
    	os.makedirs(TMP_FOLDER)
    
    dl_queue_size = dl_queue.qsize()
    
    for i in range(DOWNLOADERS):
      Downloader(dl_queue, dl_queue_size, ssh).start()
    
    dl_queue.join()
    print "done"
    
    #print stdout.readlines()
    #sftp.close()
    ssh.close()
    
    #print playlists
    #sftp.put(REMOTE_SCRIPT, REMOTE_SCRIPT_PATH)
    #st_uid = sftp.stat(REMOTE_SCRIPT_PATH)
class DownloadQueue(Queue.Queue):
    def __contains__(self, item):
        with self.mutex:
            return item in self.queue
            
class Downloader(threading.Thread):

    def __init__(self, queue, size, ssh):
        self.__queue = queue
        self.__sftp = ssh.open_sftp()
        self.__size = size
        threading.Thread.__init__(self)

    def run(self):
        while not self.__queue.empty():
          current_size = self.__queue.qsize()
          try:
            item = self.__queue.get()
            
            local_filename, local_path, remote_filename, remote_path = getFilenames(item)
            
            tmp_filename = tmpFilename(local_filename)
            
            remote_size = self.__sftp.lstat(item).st_size
            
            try:
              
              print os.stat("%s/%s" % (local_path,local_filename))
            except OSError:
              print "doesnt exist"
            
            try:
              
              local_size = os.stat(tmp_filename).st_size
              if local_size == remote_size:
                print "file exists"
              else:
                raise OSError
            
            except OSError:
           
              try:              
                
                self.__sftp.get(item, tmp_filename)
                
                #os.rename(tmp_filename, "%s/%s" % (local_path,local_path))
              except IOError:
                print "could not download %s" % item
            #print item
            #print head
            print remote_filename
            
            
          except Queue.Empty:
            break
          finally:
          	
            print "%d/%d" % ((self.__size - current_size) + 1, self.__size)
            self.__queue.task_done()
            
    
    
    #print st_uid
    
    #xml_file = tempfile.TemporaryFile()
    
    #sftp.get(ITUNES_XML_PATH,xml_file.name, callback=callback)
    
    #xml_library = plistlib.readPlist(xml_file)
    
    #print xml_file
    
