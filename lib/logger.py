from logging import handlers
import logging
import re
import os
from config import config



class PLog(object):

    context = ''

    def __init__(self, context = ''):
        if context.endswith('.main'):
            context = context[:-5]

        self.context = context
        self.logger = logging.getLogger()
        

    def info(self, msg, replace_tuple = ()):
        self.logger.info(self.addContext(msg, replace_tuple))

    def debug(self, msg, replace_tuple = ()):
        self.logger.debug(self.addContext(msg, replace_tuple))

    def error(self, msg, replace_tuple = ()):
        self.logger.error(self.addContext(msg, replace_tuple))

    def warning(self, msg, replace_tuple = ()):
        self.logger.warning(self.addContext(msg, replace_tuple))

    def critical(self, msg, replace_tuple = ()):
        self.logger.critical(self.addContext(msg, replace_tuple), exc_info = 1)

    def addContext(self, msg, replace_tuple = ()):
        return '[%+15.15s] %s' % (self.context[-15:], self.safeMessage(msg, replace_tuple))

    def safeMessage(self, msg, replace_tuple = ()):

        try:
            msg = msg % replace_tuple
        except:
            try:
                if isinstance(replace_tuple, tuple):
                    msg = msg % tuple([ss(x) for x in list(replace_tuple)])
                else:
                    msg = msg % ss(replace_tuple)
            except Exception, e:
                self.logger.error(u'Failed encoding stuff to log "%s": %s' % (msg, e))

        return msg
