# -*- coding: utf-8 -*-
# !/usr/bin/python

# Author: Cuilei, Dengyan
# Create date: Jun 10th, 2011
# Last modified: Aug 19th, 2011

import os
import re
import time

import commands
import Logging

class Openvswitch(object):
    def __init__(self):
        self.logger = Logging.get_logger('hicloud.vmc.Openvswitch')
	self.logger.info("init a Openvswitch")
	self.d = 10
	print "init a Openvswitch"

    """ This class implements to create bridge, tap, and assign the tap to certain vlan """

    def func1(self, a, b, c):
	return a+b+c+self.d

    # create a gre port in bridge br0
    def makeGRE(self, destination_ip):
	try:
	    ret = commands.getstatusoutput("ifconfig br0")
	    if ret[0]==0:
	    	cmd = "echo 123456 | sudo -S ovs-vsctl add-port br0 gre1 -- set interface gre1 type=gre option:remote_ip=%s"%destination_ip
	    	self.logger.info('execute netword cmd: %s' % cmd)
            	ret = commands.getstatusoutput(cmd)
	    	self.logger.info('make GRE tunnel cmd result: %s' % ret[0])
	    else:
		self.logger.error("bridge br0 doesn't exist")
	except Exception as err:
            err_info = "make GRE tunnel error: " + str(err)
            raise Exception(err_info)

    def __sleep(self):
        time.sleep(0.1)

    # 获得当前机器的网关
    def __get_gateway(self):
        self.logger.info('***** __get_gateway is running *****')
        # get host's gateway
        gateway = ""
        try:
            lines = commands.getstatusoutput("cat /etc/network/interfaces")
            ret = re.search('gateway [0-9|.]+', lines[1])
            if ret==None:
                # can't get gateway info
                ret = commands.getstatusoutput("ip route show")
		cmd = "ip route show"
		self.logger.info("execute cmd %s result:%s"%(str(cmd),str(ret[0])))
                if ret[1].strip() == "":
                    # can't get gateway
                    raise Exception("Can not get gateway infomation in local host")
                else:
                    ret = re.search('default via [0-9|.]+', ret[1])
                    if ret == None:
                        raise Exception("Can not get gateway information in local host")
                        return -1
                    else:
                        ret = ret.group().strip()
                        gateway = ret.split()[2].strip()
                        return gateway
            else:
                ret = ret.group().strip()
                gateway = ret.split()[1]
                return gateway
        except Exception as err:
            err_info = "Get host gateway error: " + str(err)
            raise Exception(err_info)

    def exe_command(self, command):
        self.logger.info('***** exe_command is running *****')
        try:
            pipe = os.popen(command, "r")
            result = pipe.readlines()
            pipe.close()
            return result
        except Exception as err:
            pipe.close()
            return None

    # 获取机器网卡
    def __get_default_nic(self):
        self.logger.info('***** __get_default_nic is running *****')
        # Get default nic in use, nic should be set by Administrator, modify later
        try:
            routes = self.exe_command("/sbin/route -n | sed '1,2d' | grep 'UG'")
            if routes == None or len(routes) == 0 or routes[0].strip() == "":
                # get ip from /etc/network/interfaces 
                network_path = '/etc/network/interfaces'
                self.logger.info("network_path: %s" % network_path)
                if os.path.exists(network_path):
                    nic = 'eth0'
                    f = None
                    try:
                        with open(network_path) as f:
                            lines = f.readlines()
                            for line in lines:
                                if line.find('static') != -1 and line.find('iface') != -1:
                                    nic = line.strip()[1]
                                    break
                    except Exception as err:
                        raise Exception("Get network error: " + str(err))
                    finally:
                        if f != None:
                            f.close()
                        return nic
            else:
                return routes[0].split()[7]
        except Exception as err:
            self.logger.info("Error in get_default_interface" + str(err))
            raise Exception("Error in get_default_interface" + str(err))
            return "eth0"

    def __create_bridge(self, br_name, g_vs_type):
        self.logger.info('***** __create_bridge is running *****')
        if g_vs_type == "ovs-vsctl":  # TODO: use global variable
            br_cmd = "ovs-vsctl"
        else:
            br_cmd = "brctl"

        self.logger.info('br_cmd value is: %s' % br_cmd)
        try:
            # cmd = "%s list-br | grep %s" % (br_cmd, br_name) # brctl show | grep br
            # 获取网卡信息
            cmd = "ifconfig %s | grep addr" % br_name
            ret = commands.getstatusoutput(cmd)
            self.logger.info('get gateway cmd: %s, result: %s, %s' % (cmd, ret[0], ret[1]))
            # if ret[1].strip() != "": # bridge exist
            if ret[0] == 0:
                # 判断当前机器是否设置ip
                ret = re.search("addr:[0-9|.]+", ret[1]).group()
                self.logger.info('current ip: %s' % ret)
                if ret.strip() == "":
                    return -2  # need assign address
                else:
                    return 0  # ok
            else:
                # 配置网卡
                cmd = "echo 123456 | sudo -S ovs-vsctl add-br %s" % br_name  # brctl addbr bridge
                ret = commands.getstatusoutput(cmd)
                self.logger.info('create bridge cmd: %s, result: %s' % (cmd, ret[1]))
                if ret[0] != 0:
                    err_info = "Create bridge %s error: %s" % (br_name, ret[1])
                    raise Exception(err_info)
                else:
                    return -2
        except Exception as err:
            self.logger.info('__create_bridge is error: %s' % err)
            raise Exception(err)
            return -1

    def create_br0(self, g_vs_type):
        self.logger.info('***** create_br0 is running *****')
        # This function should not be here
        if g_vs_type == "ovs-vsctl":  # TODO: use global variable
            br_cmd = "ovs-vsctl"
        else:
            br_cmd = "brctl"

        nic = self.__get_default_nic()
        self.logger.info('br_cmd value is: %s, nic value is: %s' % (br_cmd, nic))
        try:
            ret = self.__create_bridge('br0', br_cmd)
            if ret == -1:  # create failed 无网卡且创建失败
                return -1
            elif ret == 0:  # bridge is created before 网卡存在并且有IP
                return 0
            else:           #无网卡创建成功，并配置IP信息等
                # 添加网络配置信息
                # new a bridge
                # get eth0's ip and netmask
                cmd = "echo 123456 | sudo -S ifconfig %s | grep Mask" % nic    ###nic是机器网卡名称
                self.logger.info('mask cmd value: %s' % cmd)
                ip = "192.168.1.1"
                netmask = "255.255.255.0"
                try:
                    ret = commands.getstatusoutput(cmd)  # for debian system
		    self.logger.info("execute cmd %s result:%s"%(str(cmd),str(ret[0])))
                    ret_list = ret[1].split()
                    ip = ret_list[1].split(':')[1]
                    netmask = ret_list[3].split(":")[1]
                except Exception as err:
                    self.logger.error('netword config is error: %s' % err)
                    import socket
                    import fcntl
                    import struct
                    ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', nic))[20:24])
                    netmask = "255.255.255.0"  # TODO method to get netmask

                gateway = self.__get_gateway()
                self.logger.info('gateway value is: %s' % gateway)
                if gateway == -1:
                    raise Exception("Configure br0's ip error, can't get gateway")
                # the commands below is reconfigure vmc's ip from eth0 to br0
                cmds = ["echo 123456 | sudo -S ifconfig br0 %s netmask %s" % (ip, netmask),  # configure br0's ip and netmask
                        "echo 123456 | sudo -S ifconfig br0 up",  # up br0
                        "echo 123456 | sudo -S ifconfig %s up" % (nic),  # ifup nic
                        "echo 123456 | sudo -S ifconfig %s 0.0.0.0" % (nic),
                        "echo 123456 | sudo -S %s add-port br0 %s" % (br_cmd, nic),  # add eth0 to br0
                        "echo 123456 | sudo -S route add default gw %s " % (gateway)]  # add gateway to connect outside

                self.logger.info('cmds value is: %s' % cmds)
                # execute cmds
                for cmd in cmds:
                    try:
                        self.logger.info('execute netword cmd: %s' % cmd)
                        ret = commands.getstatusoutput(cmd)
			self.logger.info("execute cmd %s result:%s"%(str(cmd),str(ret[0])))
                    except Exception as err:
                        self.logger.error('execute netword is error: %s' % err)
                        raise Exception("Execute cmd error: " + str(err))
                    time.sleep(0.2)  # ok?
                return 0
        except Exception as err:
            self.logger.error('create_br0 is error: %s' % err)
            raise Exception("Configure br0's ip error:" + str(err))

    def del_br0(self):
        self.logger.info('***** del_br0 is running *****')
        try:
            cmd = "echo 123456 | sudo -S ovs-vsctl list-br | grep br0"
	    self.logger.debug("debug1")
            ret = commands.getstatusoutput(cmd)
	    self.logger.debug("debug2")
            if ret[0] == 256:
                self.logger.info("br0 has already been deleted")
                return 0
	    self.logger.debug("debug3")
            cmd = "echo 123456 | sudo -S ovs-vsctl list-ports br0 | grep tap"
            ret = commands.getstatusoutput(cmd)
            if ret[0] == 0:
		'''
                self.logger.info("you can`t delete br0 because there are still some tap on it")
		'''
		try:
            		tap_names = ret[1].split('\n')
			for i in range(0, len(tap_names)):
				tap_name = tap_names[i].strip()
				tap_names[i] = tap_name
				self.logger.info("tap_name:%s"%(str(tap_name)))
            		for tap_name in tap_names:
                		ret = self.__ifdown_tap(tap_name)
                		#if ret != 0:
                    		#	raise Exception("Ifdown tap %s failed " % (tap_name))  # no serious effect

                		# step 3: delete tap from bridge
                		ret = self.__del_tap_from_br0(tap_name)
                		if ret != 0:
                    			raise Exception("Delete tap %s from bridge" % (tap_name))

                		# step 4: delete tap
				if tap_name != "eno1":
                			ret = self.__del_tap(tap_name)
                			if ret != 0:
                    				raise Exception("Delete tap %s failed" % (tap_name))
        	except Exception as e:
            		# raise Exception, "Shutdown tap failed: " + str(err)
			self.logger.error("error in del ports from br0: %s"%(str(e)))
            		return -1
	    if(True):	
                cmd = "echo 123456 | sudo -S ifconfig br0 | grep Mask"
                try:
                    ret = commands.getstatusoutput(cmd)
                    ret_list = ret[1].split()
                    ip = ret_list[1].split(':')[1]
                    netmask = ret_list[3].split(":")[1]
		    self.logger.info("ip: %s"%(str(ip)))
		    self.logger.info("netmask: %s"%(str(netmask)))
                except Exception as err:
                    import socket
                    import fcntl
                    import struct
                    ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', nic))[20:24])
                    netmask = "255.255.255.0"  # TODO method to get netmask

                cmd = "route | grep default"
                try:
                    ret = commands.getstatusoutput(cmd)  # for debian system
                    ret_list = ret[1].split()
                    gateway = ret_list[1]
		    self.logger.info("gateway: %s"%(str(gateway)))
                except Exception as err:
                    return -1
		'''
                cmd = "echo 123456 | sudo -S ovs-vsctl del-port br0 gre1"
                try:
                    ret = commands.getstatusoutput(cmd)
                    self.logger.info("execute %s result: %s"%(cmd, ret[0]))
                except Exception as err:
                    self.logger.error("delete gre tunnel error: %s"%(str(err)))
		    return -1
		'''
                cmds = ["echo 123456 | sudo -S ifconfig eno1 %s netmask %s" % (ip, netmask), \
                        "echo 123456 | sudo -S ifconfig br0 0.0.0.0", \
                        "echo 123456 | sudo -S route add default gw %s" % (gateway), \
                        "echo 123456 | sudo -S ifconfig br0 down", \
                        "echo 123456 | sudo -S ovs-vsctl del-br br0"]
                for cmd in cmds:
                    ret = commands.getstatusoutput(cmd)
		    self.logger.info("result of execute %s: %s"%(str(cmd), str(ret[0])))
                if ret[0] != 0:
                    self.logger.info("Delete br0 error")
                    raise Exception(ret[1])
                else:
                    return 0
        except Exception as err:
            raise Exception("delete br0 error:" + str(err))
            return -1

    # 创建虚拟机网卡节点
    def __create_tap(self, tap_name):
        self.logger.info('***** __create_tap is running *****')
        """ create a tap device
        return:
        tapname: create a tap
        -1: fail
        """
        try:
            cmd = "echo 123456 | sudo -S ifconfig | grep " + tap_name
            res = commands.getstatusoutput(cmd)
            self.logger.info('get tap cmd: %s, result: %s, %s' % (cmd, res[0], res[1]))
            if res[1].strip() != "":
                # tap exists
		self.logger.info("port%s exists"%tap_name)
                return 0

            vmp_cmd = "echo 123456 | sudo -S openvpn --mktun --dev %s" % tap_name
            self.logger.info('execute cmd: %s' % vmp_cmd)
            res = commands.getstatusoutput(vmp_cmd)
            self.logger.info('openvpn cmd result: %s' % res[0])
            # tap_name = re.search('tap[0-9|A-Z|a-z]+', res).group()
            if res[0] == 0:  # success
		self.logger.info("create port %s succeed"%tap_name)
                return 0
            else:
                # raise Exception, "Create tap " + tap_name + " failed: " + res[1]
                return -1
        except Exception as err:
            # raise Exception, "Create tap failed: " + str(err)
            self.logger.info('create tap is error: %s' % err)
            return -1
        # older method
        # cmd = "tunctl"
        # try:
        #    ret = commands.getstatusoutput(cmd)
        #    if ret[0] == 0:
        #        ret = ret[1].split()
        #        tap = ret[1]
        #        return ret[1][1:-1].strip()
        #    else:
        #        return -1
        # except Exception as err:
        #    return -1

    def __assign_tap_to_vlan(self, tap, vlan_id):
        self.logger.info('***** __assign_tap_to_vlan is running *****')
        ''' assign the tap device to vlan '''
        try:
            br = "br0"
            cmd = "echo 123456 | sudo -S ovs-vsctl list-ports %s | grep %s" % (br, tap)
            ret = commands.getstatusoutput(cmd)
            self.logger.info('execute cmd: %s, result: %s' % (cmd, ret[1]))
            if ret[1].strip() != "":  # tap exist
                cmd = "echo 123456 | sudo -S ovs-vsctl del-port %s %s" % (br, tap)
                self.logger.info('execute cmd: %s' % cmd)
                try:
                    ret = commands.getstatusoutput(cmd)
                    self.logger.info('execute cmd result: %s' % ret[0])
                    if ret[0] != 0:
                        self.logger.info("tap %s already exits on %s and delete it error" % (tap, br))
                        return -1
                except Exception as err:
                    self.logger.error("tap %s already exits on %s and delete it error" % (tap, br))
                    return -1

            cmd = "echo 123456 | sudo -S ovs-vsctl add-port %s %s tag=%s" % (br, tap, vlan_id)
            self.logger.info('execute cmd: %s' % cmd)
            try:
                ret = commands.getstatusoutput(cmd)
                self.logger.info('execute cmd result: %s' % ret[0])
                if ret[0] == 0:
		    self.logger.info("has added port %s into bridge %s"%(tap,br))
                    return 0
                else:
                    self.logger.info("Assign tap %s to vlan %s failed" % (tap, vlan_id))
                    return -1
            except Exception as err:
                self.logger.error("Assign tap %s to vlan %s failed" % (tap, vlan_id))
                return -1
        except Exception as err:
            self.logger.error('execute __assign_tap_to_vlan is error: %s' % err)
            return -1

    # 删除vlan和tap的绑定
    def __del_tap(self, tap):
	self.logger.info("delete br0")
        cmd = "echo 123456 | sudo -S openvpn --rmtun --dev %s" % (tap)
        try:
            ret = commands.getstatusoutput(cmd)
            self.logger.info('execute cmd: %s, result: %s' % (cmd, ret[1]))
            if ret[0] == 0:
		self.logger.info("Delete %s succeed"%tap)
                return 0
            else:
                raise Exception("Delete tap failed, error: " + ret[1])
        except Exception as err:
            raise Exception("Delete a tap failed" + str(err))

    # 删除物理网卡和tap的绑定
    def __del_tap_from_br0(self, tap_name):
        self.logger.info('***** __del_tap_from_br0 is running *****')
        try:
            cmd = "echo 123456 | sudo -S ovs-vsctl list-ports br0 | grep %s" % (tap_name)
            ret = commands.getstatusoutput(cmd)
            self.logger.info('execute cmd: %s, result: %s' % (cmd, ret[1]))
            if ret[1].strip() == "":  # tap doesn't exist
                self.logger.info("tap %s does not exist on br0" % (tap_name))
                return -1
            else:
                cmd = "echo 123456 | sudo -S ovs-vsctl del-port br0 %s" % (tap_name)
                ret = commands.getstatusoutput(cmd)
            	self.logger.info('execute cmd: %s, result: %s' % (cmd, ret[1]))
                if ret[0] != 0:
                    self.logger.info("Delete tap %s from br0 error: %s" % (tap_name, ret[1]))
                    raise Exception(ret[1])
                else:
	            self.logger.info("Delete tap %s from br0 succeed" % tap_name)
                    return 0
        except Exception as e:
            # "Delete tap %s error from br0" % (tap_name))
            return -1

    # 开启网卡
    def __ifup_tap(self, tap):
        self.logger.info('***** __ifup_tap is running *****')
        cmd = "echo 123456 | sudo -S ifconfig %s up" % (tap)
        self.logger.info('execute cmd: %s' % cmd)
        try:
            ret = commands.getstatusoutput(cmd)
	    self.logger.info('execute cmd result: %s' % ret[0])
            if ret[0] == 0:
                return 0
            else:
                raise Exception("Ifup tap " + tap + "  failed: " + ret[1])
                return -1
        except Exception as e:
            raise Exception("Start tap " + tap + " failed: " + str(e))
            return -1

    # 关闭网卡
    def __ifdown_tap(self, tap):
        self.logger.info('***** __ifdown_tap is running *****')
        cmd = "echo 123456 | sudo -S ifconfig %s down" % (tap)
	self.logger.info('execute cmd: %s' % cmd)
        try:
            ret = commands.getstatusoutput(cmd)
	    self.logger.info('execute cmd result: %s' % ret[0])
            if ret[0] == 0:
                return 0
            else:
                return -1
        except Exception as e:
	    self.logger.error("error in shutdown port %s: %s"%(str(tap),str(e)))
            return -1

    # This function is no use now
    # def __write_tap_to_xml(self, tap, uuid):
    #    ''' write the tap created to uuid.xml
    #    '''
    #    xml_path = os.path.join(self.vmxmlRoot, uuid+'.xml')
    #    if not os.path.exists(xml_path):
    #        return -1
    #    dom = minidom.parse(xml_path)
    #    dom.getElementsByTagName("interface")[0].getElementsByTagName("target")[0].attributes["dev"].value = tap
    #    f = open(xml_path,'w')
    #    f.write(dom.toxml())
    #    f.close()
    #    return dom.toxml()

    def start_tap_by_name(self, vlan_id, tap_name):
	self.logger.info('***** start_tap_by_name is running *****')
	try:
            self.logger.info('tap_name value is: %s' % tap_name)
            ret = self.__create_tap(tap_name)
            if ret != 0:
               raise Exception("Create tap " + tap_name + " failed")
            self.__sleep()
            if self.__assign_tap_to_vlan(tap_name, vlan_id) == -1:  # add by cuilei, May 2016
               raise Exception("Assign tap " + tap_name + " to vlan" + vlan_id + " failed")
            self.__sleep()
            self.__ifup_tap(tap_name)
            self.__sleep()
            return 0
        except Exception as err:
            self.logger.error('execute start_tap_by_name is error: %s' % err)
            raise Exception(str(err))

    def start_tap(self, vlan_id, xmlFilename):
        self.logger.info('***** start_tap is running *****')
        i = 0
        try:
            tap_names = getTapFromDomainXML(xmlFilename)
            self.logger.info('tap_names value is: %s' % tap_names)
            for tap_name in tap_names:
                self.logger.info("tap_name: %s" % tap_name)
                ret = self.__create_tap(tap_name)
                if ret != 0:
                    raise Exception("Create tap " + tap_name + " failed")
                self.__sleep()
                # step3: assign tap to vlan
                if self.__assign_tap_to_vlan(tap_name, vlan_id[i]) == -1:  # add by cuilei, May 2016
                    raise Exception("Assign tap " + tap_name + " to vlan" + vlan_id[i] + " failed")
                    # return -1 #TODO: modify her
                i = i + 1
                self.__sleep()
                # step4: write tap name into vm's xml, no use now
                # self.__write_tap_to_xml(tap, uuid) # This step is deletetd beacuse tapname is written to xml on deployment
                # self.__sleep()
                # step5: start up tap device
                self.__ifup_tap(tap_name)
                self.__sleep()
                # step6: write tap to file, no use now
                # self.setTap(uuid, tap)
                # self.__sleep()
            return 0
        except Exception as err:
            self.logger.error('execute start_tap is error: %s' % err)
            raise Exception(str(err))

    def shutdown_tap(self, xmlFilename):
        self.logger.info('***** shutdown_tap is running *****')
        # TODO: delete tap fail won't cause serious effect
        try:
            # step 1: get tap from xml
            tap_names = getTapFromDomainXML(xmlFilename)
            for tap_name in tap_names:
                # step 2: ifdown tap
                ret = self.__ifdown_tap(tap_name)
                if ret != 0:
                    raise Exception("Ifdown tap %s failed " % (tap_name))  # no serious effect

                # step 3: delete tap from bridge
                ret = self.__del_tap_from_br0(tap_name)
                if ret != 0:
                    raise Exception("Delete tap %s from bridge" % (tap_name))

                # step 4: delete tap
                ret = self.__del_tap(tap_name)
                if ret != 0:
                    raise Exception("Delete tap %s failed" % (tap_name))
	    return 0
        except Exception as e:
            # raise Exception, "Shutdown tap failed: " + str(err)
            return -1

    def exeCmd(self, cmd):
	ret = commands.getstatusoutput(cmd)
	self.logger.info("execute %s result: %s"%(str(cmd), str(ret[0])))
	return ret	

    def delMirror(self):
	self.logger.info("delMirror is running")
	try:
		cmds = ["virsh destroy ubuntu-16-mirror", "virsh undefine ubuntu-16-mirror", "echo 123456 | sudo -S ifconfig tap_mirror down", "echo 123456 | sudo -S ovs-vsctl del-port br0 tap_mirror", "echo 123456 | sudo -S openvpn --rmtun --dev tap_mirror", "echo 123456 | sudo -S ifconfig tap_mirror_an down", "echo 123456 | sudo -S ovs-vsctl del-port br0 tap_mirror_an", "echo 123456 | sudo -S openvpn --rmtun --dev tap_mirror_an"]
                for cmd in cmds:
                        ret = self.exeCmd(cmd)
		return 0
	except Exception as err:
		logger.error("delMirror error: %s"%(str(err)))
		return -1

    def setMirror(self, tap_name, select_mode, tag):
	self.logger.info("setMirror is running: get mirror tap of %s with select_mode: %s"%(str(tap_name), str(select_mode)))
	try:
		ret = self.exeCmd("echo 123456 | sudo -S ovs-vsctl show")
		if ret[0]!=0:
			return -1
		if re.search('br0', ret[1])==None:
			self.logger.error("br0 doesn't exist")
			return -1		
		if re.search(str(tap_name), ret[1])==None:
                        self.logger.error("%s doesn't exist in br0"%(str(tap_name)))
                        return -1  
                if re.search(str('tap_mirror'), ret[1])!=None:
                        self.logger.error("tap_mirror already exist in br0")
                        return -1 
		ret = self.exeCmd("echo 123456 | sudo -S virsh list --all")
		if re.search('mirror', ret[1])!=None:
                        self.logger.error("vmi with mirror tap already exists")
                        return -1   
		if (select_mode!=str("select_all")) and (select_mode!=str("select_dst_port")) and (select_mode!=str("select_src_port")):
			self.logger.error("wrong select_mode: %s"%(str(select_mode)))
			return -1
		out_port = "tap_mirror"
		if select_mode == 'select_all':
			cmds = ["echo 123456 | sudo -S openvpn --mktun --dev tap_mirror", "echo 123456 | sudo -S ovs-vsctl add-port br0 tap_mirror tag=%s"%(str(tag)), "echo 123456 | sudo -S ifconfig tap_mirror up","echo 123456 | sudo -S openvpn --mktun --dev tap_mirror_an", "echo 123456 | sudo -S ovs-vsctl add-port br0 tap_mirror_an tag=%s"%(str(tag)), "echo 123456 | sudo -S ifconfig tap_mirror_an up","echo 123456 | sudo -S ovs-vsctl -- --id=@%s get port %s -- --id=@tap_mirror get port tap_mirror -- --id=@m create mirror name=m0 %s=true output_port=@tap_mirror -- set bridge br0 mirrors=@m"%(str(tap_name), str(tap_name), str(select_mode))]
		else:
			cmds = ["echo 123456 | sudo -S openvpn --mktun --dev tap_mirror", "echo 123456 | sudo -S ovs-vsctl add-port br0 tap_mirror tag=%s"%(str(tag)), "echo 123456 | sudo -S ifconfig tap_mirror up", "echo 123456 | sudo -S openvpn --mktun --dev tap_mirror_an", "echo 123456 | sudo -S ovs-vsctl add-port br0 tap_mirror_an tag=%s"%(str(tag)), "echo 123456 | sudo -S ifconfig tap_mirror_an up", "echo 123456 | sudo -S ovs-vsctl -- --id=@%s get port %s -- --id=@tap_mirror get port tap_mirror -- --id=@m create mirror name=m0 %s=@%s output_port=@tap_mirror -- set bridge br0 mirrors=@m"%(str(tap_name), str(tap_name), str(select_mode), str(tap_name))]
		for cmd in cmds:
			ret = self.exeCmd(cmd)
			if ret[0]!=0:
				return -1
		ret = self.exeCmd("echo 123456 | sudo -S virsh define /vmc160/tap_mirror.xml")
		if ret[0]!=0:
			self.logger.error("virsh define ubuntu-16-mirror error: %s"%(str(ret[1])))
			return -1
		ret = self.exeCmd("echo 123456 | sudo -S virsh start ubuntu-16-mirror")
                if ret[0]!=0:
                        self.logger.error("virsh start ubuntu-16-mirror error: %s"%(str(ret[1])))
                        return -1
		ret = self.exeCmd("echo 123456 | sudo -S virsh dumpxml ubuntu-16-mirror | grep vnc")
		if ret[0]!=0:
                        self.logger.error("get ubuntu-16-mirror port: %s"%(str(ret[1])))
                        return -1
		vnc_port = re.search("[0-9][0-9][0-9][0-9]|-1",re.search( "port=\'[0-9]*\'", ret[1]).group(0)).group(0)
		return vnc_port

	except Exception as e:
		self.logger.error("setMirror error: %s"%(str(e)))
		return -1		

def getTapFromDomainXML(fname):
    from xml.dom import minidom
    try:
        xmldoc = minidom.parse(fname)
        interfaces = xmldoc.getElementsByTagName("interface")
        tap_names = []
        for interface in interfaces:  # parse tap name
            target = interface.getElementsByTagName("target")[0]
            tap_name = target.getAttribute("dev")
            tap_names.append(tap_name)
        return tap_names
    except Exception as e:
        raise Exception(e)

def tryMain():
    #    Openvswitch.__create_br0(self)
    logger = Logging.get_logger('hicloud.vmc.Openvswitch')
    ovs = Openvswitch()
    logger.info("try logger")
    #ovs.create_br0('ovs-vsctl')
    ovs.del_br0()
    #print ovs.setMirror('tap1', 'select_src_port', '0')
    #print ovs.delMirror()
    #ret = ovs.create_br0("ovs-vsctl")
    #ovs.start_tap_by_name(0, "tap1111")
    #ovs.start_tap_by_name(0, "tap2222")
    #ovs.makeGRE("172.20.0.235")

    '''
    tap_name = "tap1111"
    vlan_id = 0

    vswitch.start_tap(vlan_id, "./openvswitch.xml")
    raw_input("Ehter to shut down tap")
    vswitch.shutdown_tap("./openvswitch.xml")
    '''
'''
if __name__ == "__main__":
    main()
'''
#tryMain()
