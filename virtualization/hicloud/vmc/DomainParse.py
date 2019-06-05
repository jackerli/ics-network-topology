# class Name: DomainParse
# author:jch
# date:2009-06-21

import string
####import part start
from xml.dom import minidom


####import part end

##################class define
class DomainParse:
    def __init__(self, xmlFile):
        self.xmlFile = xmlFile
        self.bootScripts = []
        self.shutdownScripts = []

    def parse(self):
        try:
            file = open(self.xmlFile, "r")
            xmldoc = minidom.parse(file)
            try:
                scripts = xmldoc.getElementsByTagName("bootScript")[0].firstChild.data
                self.bootScripts = string.split(scripts, "\n")
            except:
                self.bootScripts = []

            try:
                scripts = xmldoc.getElementsByTagName("shutdownScript")[0].firstChild.data
                self.shutdownScripts = string.split(scripts, "\n")
            except:
                self.shutdownScripts = []
            file.close()
            return 0
        except Exception as e:
            raise Exception("fail to parse domain xml:" + str(e))
            return -1
##########################################################
