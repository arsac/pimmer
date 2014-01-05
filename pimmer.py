#!/usr/bin/python

from os.path import dirname
import os, sys, time, signal, traceback, logging, subprocess
from argparse import ArgumentParser

# Root path of app
base_path = dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'lib'))
from logger import *
import core
from config import config

class Pimmer(object):

  do_restart = False
    
  def __init__(self):
    
    #parse args
    parser = ArgumentParser(prog = 'pimmer.py')
    parser.add_argument('--daemon', action = 'store_true', dest = 'daemon', help = 'Daemonize the app')
    parser.add_argument('--pid_file', dest = 'pid_file', help = 'Path to pidfile needed for daemon')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increases verbosity of logging. See LOGFILE variable.')
    parser.add_argument('--console', action = 'store_true', dest = 'console', help = 'Log to console')
    
    self.options = parser.parse_args()
    #configure logger
    self.configureLogging()
    
    self.log = PLog(__name__)
  
  def configureLogging(self):
    logfile = config.get("general","log_file")
    logging.getLogger().setLevel(self.options.verbose)
  
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
    hdlr = handlers.RotatingFileHandler(logfile, 'a', 500000, 10)
    hdlr.setLevel(self.options.verbose)
    hdlr.setFormatter(formatter)
    console = self.options.console == True
    console = True
    if console and not self.runAsDaemon():
        console = logging.StreamHandler()
        console.setLevel(self.options.verbose)
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)
    logging.getLogger().addHandler(hdlr)
  
  def daemonize(self):
    try:
      from daemon import Daemon
      self.daemon = Daemon(self.options.pid_file)
      
      self.daemon.daemonize()
      print "daemon"
    except SystemExit:
      raise
    except:
      self.log.critical(traceback.format_exc())
    
  def runAsDaemon(self):
    return self.options.daemon and self.options.pid_file
        
  def exit(self, signal, frame):
    self.log.info("Shutting down Pimmer")
    core.shutdown()
    sys.exit(0)
  
  def restart(self):
    try:
      if self.runAsDaemon():
        try: self.daemon.stop()
        except: pass
    except:
      self.log.critical(traceback.format_exc())
                
    os.chdir(base_path)
    
    args = [sys.executable] + [os.path.join(base_path, os.path.basename(__file__))] + sys.argv[1:]
    self.log.info('Re-spawning %s' % ' '.join(args))
    subprocess.Popen(args)
    
  def run(self):
    
    signal.signal(signal.SIGINT, self.exit)
    signal.signal(signal.SIGTERM, lambda signum, stack_frame: sys.exit(1))
    
    try:
      core.initialize()
      core.run()
    except KeyboardInterrupt:
        pass
    except Exception:
      self.log.error(traceback.format_exc())
      
      if self.do_restart:
        self.log.info("Going to sleep 2 seconds and restart")
        time.sleep(2)
        self.restart()


#####################################
# MAIN
#####################################
if __name__ == '__main__':
  p = Pimmer()
  if p.runAsDaemon():
    p.daemonize()
  p.run()
      
sys.exit(0)