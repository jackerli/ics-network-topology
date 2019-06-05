#!/usr/bin/python
# -*- coding: utf-8 -*-

from xml.dom import minidom
import Logging
import os
import commands

logger = Logging.get_logger('hicloud.vsched.ParseNet')

def emptyLog():
    try:
    	ret = commands.getstatusoutput("echo 123456 | sudo -S echo '' > /tmp/hicloud_server.log")
    	logger.info("execute echo "" to log: %s"%str(ret[0]))
    except Exception as e:
        logger.error("execute echo "" to log: %s"%str(e))

def getNode(xml):
    try:
	xmldoc = minidom.parseString(xml.encode("utf-8"))
	nodes = xmldoc.getElementsByTagName("node")
	node_names = []
	for i in range(len(nodes)):
	    node_name = nodes[i].attributes["name"].value
	    node_names.append(node_name)
	return node_names
    except Exception as e:
	logger.error("error while getting nodes from network file: %s"%str(e))
	return []

def getLink(xml):
    try:
	xmldoc = minidom.parseString(xml.encode("utf-8"))
        links = xmldoc.getElementsByTagName("link")
        endpoint_names = []
        for i in range(len(links)):
            endpoint1_name = links[i].attributes["endpoint1"].value
	    endpoint2_name = links[i].attributes["endpoint2"].value
            endpoint_names.append(endpoint1_name)
	    endpoint_names.append(endpoint2_name)
        return endpoint_names
    except Exception as e:
        logger.error("error while getting links from network file: %s"%str(e))
	return []

def ParseNet(xml):
    emptyLog()
    '''
    xml = "<topology type='network'>\n\
<name>tryNet</name>\n\
<nodes>\n\
<node name='HMI'></node>\n\
<node name='Switch'></node>\n\
<node name='Unity'></node>\n\
<node name='AD'></node>\n\
<node name='PLC'></node>\n\
</nodes>\n\
<links>\n\
<link endpoint1='Switch' endpoint2='HMI'></link>\n\
<link endpoint1='Switch' endpoint2='Unity'></link>\n\
<link endpoint1='Switch' endpoint2='AD'></link>\n\
<link endpoint1='Switch' endpoint2='PLC'></link>\n\
</links>\n\
</topology>"
    '''
    node_names = getNode(xml)
    endpoint_names = getLink(xml)
    logger.info("name of devices in topology network:")
    logger.info(node_names)
    logger.info("links in topology network:")
    logger.info(endpoint_names)
    device_names = []
    for i in range(len(endpoint_names)/2):
    	k = i*2
    	if endpoint_names[k] == "Switch":		 
	    device_names.append(endpoint_names[k+1])
	    logger.info("connect %d devices to  %d switches in the topology network(two devices connected to one switch in one vmc)"%(len(device_names),(len(device_names)+1)/2))
    return endpoint_names
