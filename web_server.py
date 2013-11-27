#!/usr/bin/python

import os, sys, time, signal
# 
sys.path.append( './lib/' )
# 
import module_web as server
import core as core

import threading
# 
# #####################################
# # FUNCTIONS
# #####################################
# # Print basic usage
# def print_usage():
#   print "Intended Use:"
#   print "%s <BROADCAST ADDRESS>" % (sys.argv[0])
#   print "Eg: %s 0.0.0.0:8815" % (sys.argv[0])
# 
# #####################################
# # MAIN
# #####################################
# if len(sys.argv) != 2:
#   print_usage()
#   sys.exit(1)
# 
# # Run web interface
# pB_web.init()
# 
# sys.exit(0)


class WebServer(threading.Thread):

    abort = False
    running = False
    app = None
    
    def __init__(self):
        threading.Thread.__init__(self)
        self.app = server.init()
        
    def run(self):
	    
	    while True and not self.abort:
	       #try:
	       self.app.start()
	       #except:
	       
	       #self.app.start()
	       #try:
	         #self.app.start()
	       #except:
	         #self.app.stop()
	       #self.app = server.init()
	       #except Exception e 
	       #time.sleep(10)
	    
    
    def isRunning(self):
        return self.running

    def quit(self):
        self.abort = True
        self.app.stop()

    def canShutdown(self):
        return (self.abort and not self.running)