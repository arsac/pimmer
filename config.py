import ConfigParser
import os.path


class PimmerConfigParser(ConfigParser.RawConfigParser):
    def __init__(self):
        ConfigParser.RawConfigParser.__init__(self)
	
    def getlist(self,section,option):
        value = self.get(section,option)
        return list(filter(None, (x.strip() for x in value.splitlines())))

    def getlistint(self,section,option):
        return [int(x) for x in self.getlist(section,option)]


config = PimmerConfigParser()
config.readfp(open("%s/config.ini" % os.path.dirname(os.path.realpath(__file__))))