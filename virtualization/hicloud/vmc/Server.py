#!/usr/bin/python
# -*- coding: utf-8 -*-

"""vmc server for Python
          
Usage: python vmc_server.py [--daemon] ip [port]
    ip use specified server binding address
Options: 
    --daemon -- start as a daemon
    port     -- use specified server binding port (default 8989)
Examples:    
python vmc_server.py 127.0.0.1
python vmc_server.py --daemon 192.168.4.120 10000
"""

import ConfigParser
import datetime
import glob
import random
import socket
import sys
import tarfile
import tempfile
import thread
import urllib
import urllib2
import uuid
import libvirt
import yaml
import Utils
import Config
import Logging
import commands
from Utils import close_all, daemonize
from Domain import *
from DomainParse import *
from Error import *
from OpenSSH import OpenSsh
from Openvswitch import *
#from Scheduler import *
#from license import CheckLicense

IP_CHECK = re.compile('(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})')


def exe_command(command):
    try:
        pipe = os.popen(command, "r")
        result = pipe.readlines()
        return result
    except Exception as err:
        return None
    finally:
        pipe.close()


##打通和某个主机的连接
# def open_ssh(ip, user, pwd):
#    try:
#        commands.getstatusoutput('sh /usr/share/hicloud/vmc/run.sh %s %s %s' % (ip, user, pwd))
#    except Exception as err:
#        raise Exception, str(err)

# 获取网络配置中得dns服务器IP
def get_dnsserver():
    try:
        nameserverlines = exe_command("cat /etc/resolv.conf | grep  'nameserver'")
        for line in nameserverlines:
            if line.find("#nameserver") != -1:  # find #nameserver, commented
                pass
            else:
                dns = line.split()[1]  #
                return dns
    except Exception as err:
        logger.info("Get dns server error: %s" % str(err))
    return "0.0.0.0"


# 返回一个不存在的磁盘分区路径
def lookup_nbd_device():
    nbd_device_prefix = "/dev/nbd"
    for i in range(16):
        nbd_device = '%s%s' % (nbd_device_prefix, str(i))
        if not os.path.exists('%sp1' % nbd_device):
            return nbd_device
    return "/dev/nbd12"


VSWITCH = "/switch"
VM = "/vmi"
lock = thread.allocate_lock()
startVS_lock = thread.allocate_lock()
nbd_lock = thread.allocate_lock()
logger = Logging.get_logger('hicloud.vmc.Server')


def exe_timeout_command(command, timeout=10):
    ''' 在指定时间内执行shell命令；成功时返回shell输出，失败时返回None； '''
    rtn = None
    try:
        logger.info("@exe_timeout_command(), command: %s" % command)
        import subprocess, datetime, os, signal, time
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        t0 = datetime.datetime.now()
        while p.poll() is None:
            if (datetime.datetime.now() - t0).seconds < timeout: continue
            os.kill(p.pid, signal.SIGKILL)
            os.waitpid(-1, os.WNOHANG)
            logger.error("@exe_timeout_command(%s), timeout: %s seconds" % (command, str(timeout)))
            break
        if p.returncode == 0:
            rtn = p.stdout.readlines()
        elif p.returncode is not None:
            logger.error("@exe_timeout_command(%s), error: %s" % (command, str(p.stderr.readlines())))
    except Exception as err:
        logger.error("@exe_timeout_command(%s), exception: %s" % (command, str(err)))
    return rtn


# 修改虚拟机磁盘，包括计算机名、网卡配置信息
def modifyImageFile(image, xml):
    logger.info("@modifyImageFile(), image: %s" % image)
    logger.info("@modifyImageFile(), xml: %s" % xml)
    tmppath = tempfile.mkdtemp()
    logger.info("@modifyImageFile(), tmppath: %s" % tmppath)
    nbd_name = lookup_nbd_device()
    logger.info("@modifyImageFile(), nbd_name: %s" % nbd_name)

    try:
        # 挂载磁盘到本机NBD设备
        if not os.path.exists(image):
            logger.error("@modifyImageFile(), the image file does not exist")
            return False
        if exe_timeout_command('kvm-nbd -c %s %s' % (nbd_name, image), 60) is None:
            logger.error("@modifyImageFile(), fail to connect the NDB device")
            return False
        #####################################################
        t0 = datetime.datetime.now()
        while not os.path.exists('%sp1' % nbd_name):
            if (datetime.datetime.now() - t0).seconds >= 10:  # wait 10 seconds at best
                logger.error("@modifyImageFile(), fail to find the NDB partition")
                return False
        #####################################################
        if exe_timeout_command('mount %sp1 %s' % (nbd_name, tmppath), 60) is None:
            logger.error("@modifyImageFile(), fail to mount the NDB partition")
            return False
        logger.info("@modifyImageFile(), list dir(%s): %s" % (tmppath, str(os.listdir(tmppath))))

        # 提取虚拟机信息
        vNode = minidom.parseString(xml.encode("utf-8"))
        host_name = vNode.getElementsByTagName("Hostname")[0].firstChild.data
        logger.info("@modifyImageFile(), host_name: %s" % host_name)
        os_type = vNode.getElementsByTagName("OsType")[0].firstChild.data.lower()
        logger.info("@modifyImageFile(), os_type: %s" % os_type)
        os_version = vNode.getElementsByTagName("OsVersion")[0].firstChild.data.lower()
        logger.info("@modifyImageFile(), os_version: %s" % os_version)

        # 针对linux类操作系统的处理
        if os_type == 'linux':
            gDNS = ''  # DNS只有1个
            if os_version == 'debian' or os_version == 'ubuntu':
                # 配置虚拟机主机名
                with open('%s/etc/hostname' % tmppath, 'w+') as tmpf:
                    tmpf.write(host_name)

                logger.info("@modifyImageFile(linux), finish modifying /etc/hostname")
                # 配置虚拟机网卡
                tmp = ['auto lo', 'iface lo inet loopback']
                nics = vNode.getElementsByTagName("NIC")
                for i in range(len(nics)):
                    device = 'eth%s' % str(i)
                    address = nics[i].getElementsByTagName("Address")[0].firstChild.data
                    netmask = nics[i].getElementsByTagName("Netmask")[0].firstChild.data
                    gateway = nics[i].getElementsByTagName("Gateway")[0].firstChild.data
                    gDNS = nics[i].getElementsByTagName("DNS")[0].firstChild.data
                    tmp += ['', 'auto %s' % device,
                            'iface %s inet static' % device,
                            'address %s' % address,
                            'netmask %s' % netmask,
                            'gateway %s' % gateway]
                with open('%s/etc/network/interfaces' % tmppath, 'w+') as tmpf:
                    tmpf.write('\n'.join(tmp))

                logger.info("@modifyImageFile(linux), finish modifying /etc/network/interfaces")
            elif os_version == 'centos' or os_version == 'redhat':
                # 配置虚拟机主机名
                with open('%s/proc/sys/kernel/hostname' % tmppath, 'w+') as tmpf:
                    tmpf.write(host_name)

                logger.info("@modifyImageFile(linux), finish modifying /proc/sys/kernel/hostname")
                # 配置虚拟机网卡
                tmp = []
                nics = vNode.getElementsByTagName("NIC")
                for i in range(len(nics)):
                    device = 'eth%s' % str(i)
                    address = nics[i].getElementsByTagName("Address")[0].firstChild.data
                    netmask = nics[i].getElementsByTagName("Netmask")[0].firstChild.data
                    gateway = nics[i].getElementsByTagName("Gateway")[0].firstChild.data
                    gDNS = nics[i].getElementsByTagName("DNS")[0].firstChild.data
                    tmp += ['', 'DEVICE="%s"' % device,
                            'BOOTPROTO="static"',
                            'IPADDR="%s"' % address,
                            'NETMASK="%s"' % netmask,
                            'ONBOOT="yes"',
                            'TYPE="Ethernet"']
                with open('%s/etc/sysconfig/network-scripts/ifcfg-%s' % (tmppath, device), 'w+') as tmpf:
                    tmpf.write('\n'.join(tmp))

                logger.info(
                    "@modifyImageFile(linux), finish modifying /etc/sysconfig/network-scripts/ifcfg-%s" % device)

                # The /etc/sysconfig/network file is used to specify information about the desired network configuration.
                tmp = 'GATEWAY=%s' % gateway
                with open('%s/etc/sysconfig/network' % tmppath, 'a+') as tmpf:
                    if re.search('^\s*' + tmp, tmpf.read(), re.M):
                        tmpf.seek(0)
                        tmpf.write('\n%s' % tmp)

                logger.info("@modifyImageFile(linux), finish modifying /etc/sysconfig/network")
            else:
                logger.error("Unspported OS version: %s" % os_version)
                return False

            # The /etc/resolv.conf is a set of routines in the C library that provide access to the Internet Domain Name System (DNS)
            tmp = 'nameserver %s' % gDNS
            logger.info(tmp)
            # with open('%s/etc/resolv.conf' % tmppath,'w+') as tmpf:
            #    if re.search('^\s*'+tmp, tmpf.read(), re.M): tmpf.seek(0); 
            #    print >> tmpf, '\n%s' % tmp
            #    logger.info(tmp)
            tmpf = open('%s/etc/resolv.conf' % tmppath, 'a+')
            logger.info(tmpf.read())
            if re.search('^\s*' + tmp, tmpf.read(), re.M):
                tmpf.seek(0);
            tmpf.write('\n%s' % tmp)
            tmpf.close()
            logger.info("@modifyImageFile(linux), finish modifying /etc/resolv.conf")

            # The /etc/hosts contains a list of IP addresses and the hostnames that they correspond to
            with open('%s/etc/hosts' % tmppath, 'w+') as tmpf:
                tmpf.write('127.0.0.1 %s localhost' % host_name)

            logger.info("@modifyImageFile(linux), finish modifying /etc/hosts")
        # 针对windows类操作系统的处理
        elif os_type == 'windows':
            # 修改windows批处理文件的主机信息
            tmp = ["cls", "netsh -f c:\\interfaces.txt", "@echo off",
                   'reg add "HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Control\ComputerName\ComputerName" /v "ComputerName" /d "%s" /f ' % host_name,
                   'reg add "HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\Tcpip\Parameters" /v "NV Hostname" /d "%s" /f ' % host_name,
                   'reg add "HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services\Tcpip\Parameters" /v "Hostname" /d "%s" /f ' % host_name,
                   'reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName" /v "ComputerName" /d "%s" /f ' % host_name,
                   'reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" /v "NV Hostname" /d "%s" /f ' % host_name,
                   'reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" /v "Hostname" /d "%s" /f ' % host_name]
            with open('%s/NetworkConfig.bat' % tmppath, 'w+') as tmpf:
                tmpf.write('\n'.join(tmp))

            logger.info("@modifyImageFile(windows), finish modifying /NetworkConfig.bat")

            # 修改windows虚拟机网络配置文件
            nics = vNode.getElementsByTagName("NIC")
            for i in range(len(nics)):
                address = nics[i].getElementsByTagName("Address")[0].firstChild.data
                netmask = nics[i].getElementsByTagName("Netmask")[0].firstChild.data
                gateway = nics[i].getElementsByTagName("Gateway")[0].firstChild.data
                dns = nics[i].getElementsByTagName("DNS")[0].firstChild.data

                tmp = ["pushd interface ip",
                       'set address name="" source=static addr=%s mask=%s' % (address, netmask),
                       'set address name="" gateway=%s gwmetric=0' % gateway,
                       'set dns name="" source=static addr=%s register=PRIMARY' % dns,
                       'set wins name="" source=static addr=none',
                       "popd",
                       "pushd interface ip",
                       'set address name="local" source=static addr=%s mask=%s' % (address, netmask),
                       'set address name="local" gateway=%s gwmetric=0' % gateway,
                       'set dns name="local" source=static addr=%s register=PRIMARY' % dns,
                       'set wins name="local" source=static addr=none',
                       "popd"]
                break  # TODO: only the 1st take effect
            with open('%s/interfaces.txt' % tmppath, 'w+') as tmpf:
                tmpf.write('\n'.join(tmp))

            logger.info("@modifyImageFile(windows), finish modifying /interfaces.txt")
        # return successfully
        return True
    except Exception as err:
        logger.error("Execute modifyVMImage() error: %s" % str(err))
        return False
    finally:
        # 卸载磁盘从本机NBD设备
        if exe_timeout_command('umount %s' % tmppath) is None:
            logger.error("@modifyImageFile(), fail to umount the NDB partition.")
        if exe_timeout_command('kvm-nbd -d %s' % nbd_name) is None:
            logger.error("@modifyImageFile(), fail to disconnect from the NDB device.")
            if exe_timeout_command('fuser -km %s' % nbd_name) is None:
                logger.error("@modifyImageFile(), fail to kill the process using NDB device.")


# modify VM's internal network information
# 修改linux系统虚拟机网络配置信息
def modifyVMInterfaces(xml, path, linuxType):
    try:
        workPath = os.getcwd()
        linuxType = linuxType.strip()
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        nics = xmldoc.getElementsByTagName("NIC")
        for i in range(len(nics)):
            id = nics[i].attributes["id"].value
            address = nics[i].getElementsByTagName("Address")[0].firstChild.data
            netmask = nics[i].getElementsByTagName("Netmask")[0].firstChild.data
            try:
                gateway = nics[i].getElementsByTagName("Gateway")[0].firstChild.data
            except:
                gateway = None

            modify_command = 'modifyNetwork.sh -w %s -p static -t %s -i %s -m %s -d eth%s ' % (
                path, linuxType, address, netmask, id)
            command_suffix = ""

            if gateway != None:
                command_suffix += " -g %s " % gateway

            if i != 0:
                command_suffix += " -a "

            modify_command += command_suffix
            # os.system(modify_command)
            logger.info(modify_command)
            aa = commands.getstatusoutput(modify_command)
            logger.info(aa)
    except Exception as e:
        return -2
    return 0


# modify VM's hostname
# 修改linux虚拟机域名信息
def modifyVMHostname(hostname, path, linuxType):
    try:
        ret = commands.getstatusoutput("modifyHostname.sh %s %s %s" % (linuxType.strip(), hostname.strip(), path))
        return ret[0]
    except Exception as err:
        logger.error("Execute modifyHostname.sh error, %s" % err.message)
        return -1


# ******************************************************************************************************#
# 解压一个压缩包到指定目录
def extractRootfs(tar_file_name, output_path):
    """  extract rootfs's tar.gz file   """
    try:
        tar = tarfile.open(tar_file_name)
        tar.extractall(path=output_path)
        tar.close()
        return output_path
    except Exception as e:
        logger.error("exception happen when unzip VM rootfs.")
        return None


# *******************************************************************************************************#
# 下载文件到指定文件夹
def downloadRootfs(rootfs_url, output_path):
    logger.info('***** downloadRootfs is running ******')
    try:
        filename = rootfs_url.split("/")[-1]
        # if rootfs exists, don't download again
        rootfs_abspath = '%s/%s' % (output_path, filename)
        if os.path.isfile(rootfs_abspath):
            logger.info(rootfs_abspath)
            return rootfs_abspath

        # rootfs not exists
        if not os.path.exists(output_path):
            os.system("mkdir -p %s" % output_path)

        download_command = "wget %s -P %s" % (rootfs_url, output_path)
        logger.info(download_command)
        if commands.getstatusoutput(download_command)[0] != 0:
            return None

        # return absolute path of new rootfs
        return rootfs_abspath
    except Exception as e:
        logger.error("download rootfs error.")
        return None


def get_address_md5():
    logger.info('***** get_address_md5 is running *****')
    read_general_file = open('/etc/hicloud/general.yaml', 'r')
    general2dicts = yaml.load(read_general_file)
    read_general_file.close()
    portal_url = general2dicts.get('portal_url', '')
    logger.info('portal_url value: %s' % portal_url)
    try:
        get_portal_ip_cmd = "less /etc/hosts | grep '%s' | grep -v '127.0.0.1' | awk '{print $1}'" % portal_url
        logger.info('get portal ip cmd: %s' % get_portal_ip_cmd)
        portal_ips = set(commands.getstatusoutput(get_portal_ip_cmd)[1].split('\n'))
        daemon_config = Config.load(str('/etc/hicloud/daemon.yaml'))
        listen_port = daemon_config['listen_port']

        # 从portal所在的机器获取地址和md5的对应值
        address2md5 = None
        for portal_ip in portal_ips:
            try:
                md5_file = None
                md5_info_url = 'http://%s:%s/vmc/md5_address.json' % (portal_ip.strip(), listen_port)
                logger.info('md5_info_url value: %s' % md5_info_url)
                md5_file = urllib2.urlopen(md5_info_url)
                address_md5_content = md5_file.read()
                if len(address_md5_content) > 0:
                    address2md5 = eval(address_md5_content)
                    logger.info('mdt_content value: %s' % address_md5_content)
                    break
            except Exception as e:
                logger.debug('read address2md5 info is error: %s' % str(e))
            finally:
                if md5_file is not None:
                    md5_file.close()
        logger.info('address2md5 value: %s' % repr(address2md5))
        return address2md5
    except Exception as e:
        logger.error('get_address_md5 is error: %s' % str(e))
        return None


# 将本地挂载点的ip换为md5值，更换ip功能做的更改
def filter_address(vmi_path, address=None):
    logger.info('***** filter_address is running *****')
    logger.info('filter path: %s' % vmi_path)
    return vmi_path  # add by cuilei, May 2016
    '''
    try:
        address2md5 = get_address_md5()

        if address is None:
            match_result = IP_CHECK.search(vmi_path)
            if match_result is None:
                return vmi_path
            else:
                address = match_result.group()

        if address2md5 is not None and address2md5.has_key(address):
            return vmi_path.replace(address, address2md5[address])
        else:
            return vmi_path
    except Exception as e:
        logger.error('filter_address is error: %s' % str(e))
        return vmi_path
    '''


def get_vmc_address():
    logger.info('***** get_vmc_address is running *****')
    try:
	'''
        result = commands.getstatusoutput(
            "/sbin/ifconfig | grep -A 1 'br0' | grep 'inet addr:' | grep -v '127.0.0.1' | awk '{print $2}' | awk -F':' '{print $2}'")
        logger.info('vmc result: %s' % repr(result))
	if result[1].strip() == '':
            result = commands.getstatusoutput(
                "/sbin/ifconfig | grep -A 1 'eth0' | grep 'inet addr:' | grep -v '127.0.0.1' | awk '{print $2}' | awk -F':' '{print $2}'")
            if result[1].strip() == '':
                return None
            else:
                return result[1].strip()
        else:
            return result[1].strip()
	'''
	result = commands.getstatusoutput(
            "/sbin/ifconfig | grep -A 1 'br0' | grep 'inet addr:' | grep -v '127.0.0.1' | awk '{print $2}' | awk -F':' '{print $2}'")
        logger.info('vmc result: %s' % repr(result))
	if result[1].strip() == '':
                return None
        else:
                return result[1].strip().split('\n')[0]
    except Exception as e:
        return None

    # ***********************************************************************************************************#


# for clone method: get vm`s old uuid
def getUuidInfo(xml):
    logger.info('***** getUuidInfo is running ******')
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        uuid = xmldoc.getElementsByTagName("Uuid")[0].firstChild.data.strip()
        return uuid
    except Exception as e:
        logger.error("ger uuid info from vm template, happen exception")
        return None


# for cteate temp method
def getCreatetInfo(xml):
    logger.info('***** getCreatetInfo is running ******')
    # string ='<vNode><VmiUuid>a6e01d24-bed7-11e0-9b78-78e7d158fd70</VmiUuid><TempUuid>11111111-1111-1111-111111</TempUuid><TempName>template_123</TempName><Desc>NONE</Desc><OsType>windows</OsType><MemSize>200</MemSize><DiskSize>10</DiskSize><VstorePath>172.30.30.2:/usr/local/hicloud-data/vstore</VstorePath><IsoPath>172.30.30.2:/usr/local/hicloud-data/vstore/nfsbase/debian.iso</IsoPath></vNode>'
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        vmi_uuid = xmldoc.getElementsByTagName("VmiUuid")[
            0].firstChild.data  # Hope you will not be confused by uuid and temp_uuid and their non-graceful relationship
        temp_uuid = xmldoc.getElementsByTagName("TempUuid")[0].firstChild.data
        temp_name = xmldoc.getElementsByTagName("TempName")[0].firstChild.data
        desc = xmldoc.getElementsByTagName("Desc")[0].firstChild.data
        os_type = xmldoc.getElementsByTagName("OsType")[0].firstChild.data
        mem_size = xmldoc.getElementsByTagName("MemSize")[0].firstChild.data
        disk_size = xmldoc.getElementsByTagName("DiskSize")[0].firstChild.data
        vstore_path = xmldoc.getElementsByTagName("VstorePath")[0].firstChild.data
        iso_path = xmldoc.getElementsByTagName("IsoPath")[0].firstChild.data
        vmi_type = xmldoc.getElementsByTagName("VmiType")[0].firstChild.data
        return vmi_uuid, temp_uuid, temp_name, desc, os_type, mem_size, disk_size, vstore_path, vmi_type
    except Exception as e:
        logger.error("get info from vm template, happen exception: %s" % str(e))
        return None


# ***********************************************************************************************************#
# extract VM basic infomation from xml description
def getAllBasicInfo(xml):
    logger.info('***** getAllBasicInfo is running ******')
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        ref = xmldoc.getElementsByTagName("vTemplateRef")[0].firstChild.data.strip()
        hostname = xmldoc.getElementsByTagName("Hostname")[0].firstChild.data.strip()
        memory = xmldoc.getElementsByTagName("Mem")[0].firstChild.data.strip()
        cpu_cnt = xmldoc.getElementsByTagName("CpuCnt")[0].firstChild.data.strip()
        diskSize = xmldoc.getElementsByTagName("DiskSize")[0].firstChild.data.strip()
        passwd = xmldoc.getElementsByTagName("Password")[0].firstChild.data.strip()
        return ref, hostname, memory, cpu_cnt, diskSize, passwd
    except Exception as e:
        logger.error("get all basic info from vm template, happen exception")
        return None


# ***********************************************************************************************************#
# get networks information from vnode xml description the VM's xml description are defined by ourselves
def getTapNetworkSource(xml):
    logger.info('***** getTapNetworkSource is running ******')
    uuid = "11111111-1111-1111-1111111111111112"
    networkSources = []
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        nics = xmldoc.getElementsByTagName("NIC")
        for i in range(len(nics)):
            networkSources.append(uuid)
        return networkSources
    except Exception as e:
        logger.error("get tap network source happen exception")
        return None


def getBasicInfo(xml):
    logger.info('***** getBasicInfo is running ******')
    # repeatable work, similar to getAllBasicInfo()
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        hostname = xmldoc.getElementsByTagName("Hostname")[0].firstChild.data
        desc = xmldoc.getElementsByTagName("Desc")[0].firstChild.data
        mem = xmldoc.getElementsByTagName("Mem")[0].firstChild.data
        disk_size = xmldoc.getElementsByTagName("DiskSize")[0].firstChild.data
	logger.info("debug10")
        cpu_cnt = xmldoc.getElementsByTagName("CpuCnt")[0].firstChild.data
        nic_cnt = xmldoc.getElementsByTagName("NicCnt")[0].firstChild.data
        password = xmldoc.getElementsByTagName("Password")[0].firstChild.data
        vstore_ip = xmldoc.getElementsByTagName("VstoreIp")[0].firstChild.data
        logger.info("debug11")
        os_type = xmldoc.getElementsByTagName("OsType")[0].firstChild.data
        logger.info("1:%s"%(str(os_type)))
        os_version = xmldoc.getElementsByTagName("OsVersion")[0].firstChild.data
        vstore_path = xmldoc.getElementsByTagName("VstorePath")[0].firstChild.data
	logger.info("11.5")
	logger.info("%s"%(str(xml)))
        iso_path = xmldoc.getElementsByTagName("IsoPath")[0].firstChild.data
        storage_type = xmldoc.getElementsByTagName("StorageType")[0].firstChild.data
	logger.info("debug12")
        software_type = xmldoc.getElementsByTagName("SoftwareType")[0].firstChild.data
        if vstore_ip.strip() == "":
            vstore_ip = IP_CHECK.search(iso_path).group()
        if storage_type.strip() == "local":
            vstore_ip = get_vmc_address()

        # return hostname, desc, memory, disksize, cpucnt, niccnt, passwd, vstoreip, ostype, osversion, vlan, vstore_path, iso_path, storage_type, software_type
        logger.info("hostname: %s",hostname)
        logger.info("desc: %s", desc)
        logger.info("memory: %s", mem)
	logger.info("disksize: %s", disk_size)
	logger.info("cpucnt: %s", cpu_cnt)
	logger.info("niccnt: %s", nic_cnt)
	logger.info("passwd: %s", password)
	logger.info("vstoreip: %s", vstore_ip)
        logger.info("ostype: %s", os_type)
        logger.info("osversion: %s", os_version)
        logger.info("vstore_path: %s", vstore_path)
        logger.info("iso_path: %s", iso_path)
        logger.info("storage_type: %s", storage_type)
	logger.info("software_type: %s", software_type)

	if iso_path.strip() == "":
        	return hostname, desc, mem, disk_size, cpu_cnt, nic_cnt, password, vstore_ip, os_type, os_version, vstore_path, iso_path, storage_type
        else:
		return hostname, desc, mem, disk_size, cpu_cnt, nic_cnt, password, vstore_ip, os_type, os_version, vstore_path, software_type, storage_type  

    except Exception as e:
        	logger.error("get basic info from vm template error: %s" % repr(e))
        	return None


def get_vstore_info(xml):
    logger.info('****** get_vstore_info is running *****')
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        vstore_ip = xmldoc.getElementsByTagName("VstoreIp")[0].firstChild.data
        vstore_path = xmldoc.getElementsByTagName("VstorePath")[0].firstChild.data
        logger.info('vstore_ip value: %s, vstore_path value: %s' % (vstore_ip, vstore_path))
        return vstore_ip, vstore_path
    except Exception as e:
        logger.error('get_vstore_info is error: %s' % repr(e))
        return None, None


# 获取虚拟机是基于模板还是iso创建
def getDeployTypeInfo(xml):
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        deploy_type = xmldoc.getElementsByTagName("Type")[0].firstChild.data
        return deploy_type
    except Exception as err:
        logger.error("Get deploy type error: %s" % repr(err))
        return None


# 获取虚拟机存储ip和操作系统类型
def getChaosInfo(xml):
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        storage_ip = xmldoc.getElementsByTagName("VstoreIp")[0].firstChild.data.strip()
        ostype = xmldoc.getElementsByTagName("OsType")[0].firstChild.data.strip()
        vstore_path = xmldoc.getElementsByTagName("VstorePath")[0].firstChild.data.strip()
        return storage_ip, ostype, vstore_path
    except Exception as err:
        logger.error("Get storage error: %s" % repr(err))
        return None


def getTemplaterefInfo(xml):
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        ref = xmldoc.getElementsByTagName("vTemplateRef")[0].firstChild.data
        return ref
    except Exception as err:
        logger.error("Get template reference info from vm template error: %s" % repr(err))
        return None


def getIsoPathInfo(xml):
    logger.info('***** getIsoPathInfo is running *****')
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        path = xmldoc.getElementsByTagName("IsoPath")[0].firstChild.data
        logger.info('return path value: %s' % path)
        return path
    except Exception as err:
        logger.error("Get iso path info from vm template error: %s" % repr(err))
        return None


# 获取虚拟机网络信息
# Get vlan info from xml
# NOTE: vlan and nic is not matched when connect to bridge, modified later
def getVlanNetworkSource(xml):  # rewrite by cuilei, may, 2016
    logger.info("getVlanNetworkSource is running")
    vlans = []
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        #        vlan_id = xmldoc.getElementsByTagName("Vlan")[0].firstChild.data
        #        nics = xmldoc.getElementsByTagName("NIC")
        #        for i in range(len(nics)):
        #            vlans.append(vlan_id)

        nics = xmldoc.getElementsByTagName("NIC")
        for i in range(len(nics)):
            tmp_vlan = nics[i].getElementsByTagName("Vlan")[0].firstChild.data
            vlans.append(tmp_vlan)
            logger.info("vlan %s"%(tmp_vlan))
        return vlans
    except Exception as e:
        logger.error("get vlan network source happen exception, error: %s" % repr(e))
        return None


# add by cuilei, May 2016
def getDeploypath(xml):  # rewrite by cuilei, may, 2016
    deploy_path = "nfs"  # default method
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        deploy_path = xmldoc.getElementsByTagName("StorageType")[0].firstChild.data
    except Exception as e:
        logger.error("get deploy path happen exception, error: %s" % repr(e))
    return deploy_path


def getTempIP(xml):  # rewrite by cuilei, may, 2016
    ip = "127.0.0.1"  # default method
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        temp_ref = xmldoc.getElementsByTagName("vTemplateRef")[0].firstChild.data
        re_ip = re.compile(r'(?<![\.\d])(?:\d{1,3}\.){3}\d{1,3}(?![\.\d])')
        ips = re_ip.findall(temp_ref)
        logger.info("get ips %s " % repr(ips))
        if len(ips) >= 1:
            ip = ips[0]
    except Exception as e:
        logger.error("get deploy ip happen exception, error: %s" % repr(e))
    return ip


# get networks information from vnode xml description
# the VM's xml description are defined by ourselves
def getAllNetworkSource(xml):
    networkSources = []
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        nics = xmldoc.getElementsByTagName("NIC")
        for i in range(len(nics)):
            uuid = nics[i].getElementsByTagName("")[0].firstChild.data
            id = nics[i].attributes["id"].value
            networkSources.append(uuid)
        return networkSources
    except Exception as e:
        logger.error("get all network source happen exception, error: %s" % repr(e))
        return None


# ***********************************************************************************************************#
# get networks information from VM libvirt xml
# return value: networks list which represents the networks that the VM are connecting to 
def getNetworkFromDomain(xml):
    networkSources = []
    try:
        xmldoc = minidom.parseString(xml.encode("utf-8"))
        interfaces = xmldoc.getElementsByTagName("interface")

        for i in range(len(interfaces)):
            uuid = interfaces[i].getElementsByTagName("source")[0].attributes["network"].value
            networkSources.append(uuid)

        return networkSources
    except Exception as e:
        logger.error("get all interfaces happen exception, error: %s" % repr(e))
        return None


# ***************************************************************************************************************#
# 从创建虚拟机的模板中提取信息
def getDeployInfoFromVMT(url):
    logger.info('***** getDeployInfoFromVMT is running ******')
    # get vm deploy infomation from vnode xml
    try:
        logger.info("URL is: %s" % str(url))
        fsock = urllib.urlopen(url)
        xmldoc = minidom.parse(fsock)

        deployInfo = xmldoc.getElementsByTagName("DeployInfo")[0]
        method = deployInfo.getElementsByTagName("Method")[0].firstChild.data
        url = deployInfo.getElementsByTagName("URL")[0].firstChild.data
        cowdir = deployInfo.getElementsByTagName("COWDir")[0].firstChild.data
        linuxType = xmldoc.getElementsByTagName("Distribution")[0].firstChild.data
        url = url.strip()
        method = method.strip()
        linuxType = linuxType.strip()
        fsock.close()
        logger.info('url value: %s, method value: %s, linuxType: %s, cowdir: %s' % (url, method, linuxType, cowdir))
        return url, method, linuxType, cowdir
    except Exception as e:
        logger.error("get deploy info, happen exception: %s" % repr(e))
        return None, None, None, None


# 从创建虚拟机的模板中提取信息
def get_deploy_info_from_vmt(nfsmount_root, vmt_uri):
    logger.info('***** get_deploy_info_from_vmt is running ******')
    logger.info('vmt_uri value: %s' % vmt_uri)
    try:
        try:
            vmt_xml_file = urllib2.urlopen(vmt_uri)
            vmt_xml_content = vmt_xml_file.read()
            vmt_xml_file.close()
            xmldoc = minidom.parseString(vmt_xml_content)
        except Exception as e:
            # address2md5 = get_address_md5() # add by cuilei, May 2016
            # 适用于模板文件存储于独立存储，该存储必须进行了挂载
            vstore_ip = IP_CHECK.search(vmt_uri).group()
            temp_file = vmt_uri.rsplit('/', 1)[1]
            vmt_path = filter_address('%s/%s/template/%s' % (nfsmount_root, vstore_ip, temp_file), vstore_ip)
            logger.info('vmt_path: %s' % vmt_path)
            xmldoc = minidom.parse(vmt_path)

        deployInfo = xmldoc.getElementsByTagName("DeployInfo")[0]
        method = deployInfo.getElementsByTagName("Method")[0].firstChild.data.strip()
        url = deployInfo.getElementsByTagName("URL")[0].firstChild.data
        cowdir = deployInfo.getElementsByTagName("COWDir")[0].firstChild.data
        linuxType = xmldoc.getElementsByTagName("Distribution")[0].firstChild.data.strip()
        logger.info('url value: %s, method value: %s, linuxType: %s, cowdir: %s' % (url, method, linuxType, cowdir))
        return url, method, linuxType, cowdir
    except Exception as e:
        logger.error("get deploy info, happen exception: %s" % repr(e))
        return None, None, None, None


# read vm's name and xmldesc from a libvirt domain's configure xml file
def getNameFromDomainXML(fname):
    logger.info('***** getNameFromDomainXML is running ******')
    try:
        xmldoc = minidom.parse(fname)
        ref = xmldoc.getElementsByTagName("name")[0]
        name = ref.firstChild.data
        xmldesc = xmldoc.toxml()
        return (name, xmldesc)
    except Exception as e:
        logger.error("happen exception when read domain, error: %s" % repr(e))
        return None


def getTapFromDomainXML(fname):
    logger.info('***** getTapFromDomainXML is running ******')
    try:
        xmldoc = minidom.parse(fname)
        interfaces = xmldoc.getElementsByTagName("interface")
        tap_names = []
        for interface in interfaces:  # parse tap name
            target = interface.getElementsByTagName("target")[0]
            tap_name = target.getAttribute("dev")
            tap_names.append(tap_name)
        return tap_names
    except Exception as err:
        logger.error("Get tapname from xml %s errori: %s" % (fname, repr(err)))
        raise Exception(err)


# 启动tap
def modifyVMXML(networkUUIDs, xmlFilename):
    logger.info('***** modifyVMXML is running ******')
    res = commands.getstatusoutput("openvpn --mktun --dev tap")[1]
    tap = re.search('tap[0-9]+', res).group()
    os.system("ifconfig %s up" % tap)
    cmd = "ovs-vsctl add-port %s %s" % (networkUUIDs[0:13], tap)
    os.system(cmd)
    logger.info("add vm tap to vswitch,%s" % cmd)

    xmldoc = minidom.parse(xmlFilename)
    xmldoc.getElementsByTagName("interface")[0].getElementsByTagName("target")[0].attributes["dev"].value = tap
    f = open(xmlFilename, 'w')
    f.write(xmldoc.toxml())
    f.close()
    return xmldoc.toxml()


# read image path from libvirt xml
def getImagePathFromDomainXML(fname):
    image_path = ""
    try:
        for disk in minidom.parse(fname).getElementsByTagName("disk"):
            if disk.getAttribute('device') == "disk":
                image_path = disk.getElementsByTagName("source")[0].getAttribute('file')
                break
    except Exception as e:
        logger.error("@getImagePathFromDomainXML, error: %s" % repr(e))
    finally:
        return image_path


# ***************************************************************************************************************#
# get cdrom url from vnode xml
def getCdromURLFromURL(url):
    logger.info('***** getCdromURLFromURL is running ******')
    try:
        fsock = urllib.urlopen(url)
        xmldoc = minidom.parse(fsock)
        ref = xmldoc.getElementsByTagName("DeployInfo")[0]
        cdrom_url = ref.getElementsByTagName("Cdrom")[0].firstChild.data
        cdrom_url = cdrom_url.strip()
        return cdrom_url
    except Exception as e:
        logger.info("Failed to get cdrom url from vnode xml file, error: %s" % repr(e))
        return ""


# ***************************************************************************************************************#
# write xml information to a file
def saveXml2File(xml, path, filename):
    logger.info('***** saveXml2File is running ******')
    try:
        if not os.path.exists(path):
            os.mkdir(path)
        if not os.path.exists(filename):
	    os.system('touch %s' % filename)
	cmd = 'echo 123456 | sudo -S chmod 777 %s'%(str(filename))
	ret = commands.getstatusoutput(cmd)
	logger.debug('exe %s result:%s'%(str(cmd), str(ret[0])))
        temp_file = open(filename, "w")
        temp_file.write(xml.encode("utf-8"))
	return 0
    except Exception as e:
        logger.error("create file or make directory error: %s" % str(e))
	return 1


# ***************************************************************************************************************#
# The below operations are used for VMC xml desc
def get_basic_info_from_VMC_desc(xml):
    logger.info('***** get_basic_info_from_VMC_desc is running ******')
    try:
        dom = minidom.parseString(xml.encode("utf-8"))
        portal_url = dom.getElementsByTagName("PortalUrl")[0].firstChild.data
        portal_ip_xml = dom.getElementsByTagName("PortalIp")
        if len(portal_ip_xml) == 0:
            portal_ip = None
        else:
            portal_ip = portal_ip_xml[0].firstChild.data.split('\n')
        logger.info('portal_url value: %s, portal_ip vlaue: %s' % (portal_url, portal_ip))
        return portal_url, portal_ip
    except Exception as err:
        logger.error('get portal info is error: %s' % repr(err))
        return ''


# 添加主机后修改配置文件中得汇报地址
def change_portal_url(portal_url):
    logger.info('***** change_portal_url is running *****')
    general_path = '/etc/hicloud/general.yaml'
    try:
        read_general_file = open(general_path, 'r')
        dicts = yaml.load(read_general_file)
        read_general_file.close()

        dicts['portal_url'] = portal_url
        write_general_file = open(general_path, 'w')
        dict_keys = (
            'prefix', 'log_dir', 'run_dir', 'tmp_dir', 'data_dir', 'cache_dir', 'script_dir', 'www_dir', 'capabilities',
            'portal_url', 'vsaas_portal_url')
        for key in dict_keys:
            if not dicts.has_key(key):
                logger.info('%s not in general.yaml' % key)
                continue

            if key == 'capabilities':
                config_line = '%s: %s \r\n' % (key, dicts[key])
            else:
                config_line = '%s: \"%s\" \r\n' % (key, dicts[key])
            write_general_file.write(config_line)
        write_general_file.close()
        return 0
    except Exception as err:
        logger.error('edit portal_url is error: %s' % repr(err))
        return -1


# 添加主机后修改hosts文件中portal的域名解析
def change_portal_host(portal_url, portal_ips):
    logger.info('***** change_portal_host is running *****')
    portal_url = portal_url.replace('http://', '').strip()
    host_file = '/etc/hosts'
    hosts_cache_items = []
    original_file = open(host_file, 'r')
    current_host_config = []
    # 解析原始/etc/hosts文件
    for line in original_file.readlines():
        line = line.strip()
        if len(line) == 0:
            #            hosts_cache_items.append('\n')
            continue

        # 保留原有注释信息
        if line[0] == '#':
            hosts_cache_items.append(line)
            continue

        # 保留无关的域名解析配置
        domain_items = line.split()
        if portal_url not in domain_items:
            hosts_cache_items.append('\t'.join(domain_items))
            continue

        # 添加portal所在的主机时保留原有的主机名设置信息
        if domain_items[0].strip() == '127.0.0.1' or domain_items[0].strip() in portal_ips:
            hosts_cache_items.append('\t'.join(domain_items))
            continue

        # 历史域名解析设置
        current_host_config.append(domain_items)
    original_file.close()
    logger.info('analysis /etc/hosts is finished')

    hosts_cache_items.append('\n')
    # 加入portal的域名解析信息
    if type(portal_ips) is list:
        # portal主机使用多网卡，ip地址不确定时
        for portal_ip in portal_ips:
            portal_ip = portal_ip.strip()
            if portal_ip == '127.0.0.1':
                continue

            host_item = '%s\t%s' % (portal_ip, portal_url)
            if host_item in hosts_cache_items:
                continue

            hosts_cache_items.append(host_item)
    else:
        host_config = '%s\t%s' % (portal_ips, portal_url)
        logger.info('add host config: %s' % host_config)
        if host_config not in hosts_cache_items:
            hosts_cache_items.append(host_config)

    # 重写/etc/hosts文件
    write_host_file = open(host_file, 'w')
    for item in hosts_cache_items:
        write_host_file.write('%s\n' % item)
    write_host_file.close()
    logger.info('add portal ip is successful')


# *****************************************************************************************#
def createVMImage(osType, rootfsFileName, vmImagePath, hostname, diskSize, xml, uuid=""):
    logger.info('***** createVMImage is running *****')
    try:
        osType = osType.strip()
        osType = osType.lower()
        logger.info('osType value: %s' % osType)
        if osType.find("windows") != -1:
            dns = ""
            xmldoc = minidom.parseString(xml.encode("utf-8"))
            nics = xmldoc.getElementsByTagName("NIC")
            id = nics[0].attributes["id"].value
            address = nics[0].getElementsByTagName("Address")[0].firstChild.data
            netmask = nics[0].getElementsByTagName("Netmask")[0].firstChild.data
            try:
                gateway = nics[0].getElementsByTagName("Gateway")[0].firstChild.data
            except:
                gateway = "0"

            dns = get_dnsserver()
            network_info = "%s:%s:%s:%s" % (address, netmask, gateway, dns)

            # 创建windows虚拟机镜像
            createKvmImageShell = "windows_deploy.sh %s %s/%s.img %s %s %s" % (
                rootfsFileName, vmImagePath, hostname, diskSize, hostname, network_info)
            logger.info("Execute cmd: %s" % createKvmImageShell)
            ret = commands.getstatusoutput(createKvmImageShell)
            if ret[0] % 256 != 0:
                return None

            logger.info("Ret is %s" % str(ret[1]))
            vm_image_absFileName = '%s/%s.img' % (vmImagePath, hostname)
            logger.info('vm_image_absFileName value: %s' % vm_image_absFileName)
            return vm_image_absFileName
        else:
            # need tar file
            extract_rootfs_output_path = '%s/fs' % vmImagePath
            if not os.path.exists(extract_rootfs_output_path):
                os.system("mkdir -p %s" % extract_rootfs_output_path)

            extract_rootfs_output_path = extractRootfs(rootfsFileName, extract_rootfs_output_path)
            logger.info('extract_rootfs_output_path value: %s' % extract_rootfs_output_path)
            if extract_rootfs_output_path == None:
                return None

            vmImagePath = "%s/%s" % (vmImagePath, hostname)
            createKvmImageShell = "create_kvm_image.sh %s %s %s %s %s " % (
                extract_rootfs_output_path, vmImagePath, diskSize, osType, uuid)
            logger.info('createKvmImageShell value: %s' % createKvmImageShell)
            modifyVMHostname(hostname, extract_rootfs_output_path, osType)
            modifyVMInterfaces(xml, extract_rootfs_output_path, osType)

            os.system(
                "sed -i \"s/^exit 0/setterm -blank 0 -powerdown 0\\nexit 0/\" %s/etc/rc.local" % extract_rootfs_output_path)
            # os.system("sed -i -e \"s/^\(BLANK_TIME\)=.*/\\1=0/\" -e \"s/^\(POWERDOWN_TIME\)=.*/\\1=0/\" " + extract_rootfs_output_path + "/etc/console-tools/config")

            sysctl = open("%s/etc/sysctl.conf" % extract_rootfs_output_path, "a")
            sysctl.write("\nnet.ipv4.ip_forward=1\n")
            sysctl.close()

            # 创建linux虚拟机镜像
            if commands.getstatusoutput(createKvmImageShell)[0] != 0:
                return None
            os.system("rm -R %s" % extract_rootfs_output_path)
            vm_image_absFileName = '%s.img' % vmImagePath
            logger.info('vm_image_absFileName value: %s' % vm_image_absFileName)
            return vm_image_absFileName
    except Exception as e:
        logger.error("error when creating VM image")
        sys.stdout.flush()
        return None


# *****************************************************************************************#
def get_first_tap_name(uuid):
    try:
        tap_name = "tap%s%s" % (uuid[0:8], uuid[9:13])
        return tap_name
    except Exception as err:
        return 'tap111111111111'  # should modify


def get_next_tap_name(tap_name):
    # support 16 nics at most, please modify more for >16 nics
    cnt = 16
    src = '0123456789abcdef'
    dst = '123456789abcdef0'
    src_index = tap_name[-1]
    for i in range(16):
        if src[i] == src_index:
            tap_name = tap_name[0:-1] + dst[i]
            break
    return tap_name


# 创建虚拟机KVM模板
def makeVMConfigureXML(hostname, uuid, memory, vcpu, vmImageFilePath, networkSources, type=0, passwd=None,
                       cdrom_path=None):
    logger.info('***** makeVMConfigureXML is running *****')
    try:
        # <input type='mouse' bus='ps2'/>
        inputDevice = InputDevice("tablet", "usb")

        # <graphics type='vnc' port='-1' listen='127.0.0.1'/>
        graphicalFramebuffer = GraphicalFramebuffer("vnc")
        graphicalFramebuffer.setPort("-1")
        graphicalFramebuffer.setListen("0.0.0.0")
        # graphicalFramebuffer.setPassword(passwd)
        diskDevice = DiskXml("file", "disk")
        diskDevice.setSource(vmImageFilePath)
        diskDevice.setDriver('qemu', 'qcow2')
        # if type == 0:
        #    diskDevice.setTarget('vda','virtio')
        # else:
        diskDevice.setTarget('hda', 'ide')

        # <disk type='file' device='cdrom'>
        #      <source file='.../..iso'/>
        #      <target dev='hdc' bus='ide'/>
        # </disk>
        if cdrom_path != None:
            diskDevice2 = DiskXml("file", "cdrom")
            diskDevice2.setSource(cdrom_path)
            diskDevice2.setTarget('hdc', 'ide')
            logger.info("cdrom_path found")
        else:
            logger.info("cdrom_path not found")

        # <emulator>/usr/bin/qemu-kvm</emulator>
        if type == 1:
            emulator = EmulatorXml("/usr/bin/kvm-win")
        else:
            emulator = EmulatorXml("/usr/bin/kvm")

        if cdrom_path != None:
            devices = [inputDevice, diskDevice, diskDevice2, emulator, graphicalFramebuffer]
            logger.info("diskDevice2 added")
        else:
            devices = [inputDevice, diskDevice, emulator, graphicalFramebuffer]
            logger.info("diskDevice2 not found")

        # modify by cuilei, set tap_name
        # tap_name = "tap" + uuid[0:8] + uuid[9:13]
        tap_name = get_first_tap_name(uuid)
        logger.info(tap_name)

        for i in range(len(networkSources)):
            # interfaceDevice = NetworkInterfaceXml("network")
            interfaceDevice = NetworkInterfaceXml("ethernet")
            mac = networkSources[i].getElementsByTagName("MAC")[0].firstChild.data
            logger.info("MAC(0): %s", mac)
            interfaceDevice.setMac(mac)
            try:
                interfaceDevice.setTarget(tap_name)  # TODO set target or set source
            except Exception as e:
                logger.error("write tap to xml failed: %s", e)
                return None

            interfaceDevice.setScript("no")
            # interfaceDevice.setSource(networkSources[i])
            # interfaceDevice.setModel("virtio") #TODO
            interfaceDevice.setModel("rtl8139")
            devices.append(interfaceDevice)
            # get next tap name
            tap_name = get_next_tap_name(tap_name)
            logger.info(tap_name)

        domain = DomainXml("kvm", hostname, uuid)

        # vcpu default value is 1
        # current Memory is equal to memory
        vcpu = vcpu
        domain.setBasicResources(memory, memory, vcpu)

        # setLifecycleControl (self,on_poweroff,on_reboot,on_crash)
        # <on_poweroff>destroy</on_poweroff>
        # <on_reboot>restart</on_reboot>
        # <on_crash>destroy</on_crash>
        domain.setLifecycleControl("destroy", "restart", "destroy")

        # set clock
        # <clock offset='utc'/>
        # setTimeKeeping(self, time)
        domain.setTimeKeeping("utc")
        domain.setFeatures()

        # set operating system booting
        # setBIOSBootloader(self,type,loader,dev,arch,machine)
        domain.setBIOSBootloader("hvm", "", "hd", "", "")
        domain.setDevices(devices)

        # domain xml for vm
        logger.info("Get domain xml successfully")
        domainXML = domain.toXml()
        logger.info("OK")
        return domainXML
    except Exception as e:
        logger.error('make vm config xml is error: %s' % repr(e))
        return None


def mk_dir(dir):
    dir_list = dir.strip("/").split("/")
    path = ""
    for i in range(0, len(dir_list)):
        path = '%s/%s' % (path, dir_list[i])
        if not os.path.exists(path):
            os.mkdir(path)

###处理xml并转换成相应结构存储到tmp_file文件中
def update_vmi_info(uuid, tmp_file, xml):
    logger.info('***** update_vmi_info is running ******')
    sub_tmp_path = tmp_file.rsplit('/', 1)[0]
    logger.info('tmp_file: %s, sub_tmp_path: %s' % (tmp_file, sub_tmp_path))
    if not os.path.exists(sub_tmp_path):
        os.system('mkdir -p %s' % sub_tmp_path)
    if not os.path.exists(tmp_file):
        os.system('touch %s' % tmp_file)

    vmi_info = open(tmp_file, 'r')
    try:
        info_content = vmi_info.read().strip()
        vmi_info.close()
        if len(info_content) == 0:
            vmi2info = {}
        else:
            vmi2info = eval(info_content)

        doc = minidom.parseString(xml.encode("utf-8"))
        if vmi2info.has_key(uuid):
            tmp2info = vmi2info[uuid]
        else:
            tmp2info = {}

        tmp2info['os_type'] = doc.getElementsByTagName('OsType')[0].firstChild.data.strip()
        tmp2info['os_version'] = doc.getElementsByTagName('OsVersion')[0].firstChild.data.strip()
        tmp2info['iso_path'] = doc.getElementsByTagName('IsoPath')[0].firstChild.data.strip()
        
        max2address = {}
        nics = doc.getElementsByTagName('NIC')
        for nic in nics:
            address = nic.getElementsByTagName('Address')[0].firstChild.data.strip()
            mac = nic.getElementsByTagName('MAC')[0].firstChild.data.strip()
            max2address[mac] = address
        tmp2info['interfaces'] = max2address
        vmi2info[uuid] = tmp2info

        vmi_file = open(tmp_file, 'w')
        vmi_file.write(repr(vmi2info))
        vmi_file.close()
    except BaseException as e:
        logger.error('update_vmi_info is error: %s' % repr(e))
########
class tryServer:
    def __init__(self):
        logger.info("class tryServer is initilized")
    def func1(self,a,b,c):
        logger.info("tryServer.func1 is running")
    	return a+b+c

# ****************vmc server class********************#
class ServerClass:
    def func1(self,b,c,d):
        logger.info("tryServer.func1 is running")
        return self.a+b+c+d
    def __init__(self):
        try:
	    self.a = 11
	    config = Config.load(str('/vmc160/hicloud/vmc.yaml'))
            self.dataRoot = config["data_dir"]
            self.imageRoot = config["image_root"]
            self.vmxmlRoot = config["vmxml_root"]
            # self.snapshotXmlRoot = config["snapshot_xml_root"] // add by cuilei, 2016
            self.networkRoot = config["network_root"]
            self.rootfsRoot = config["rootfs_root"]
            self.nfsmountRoot = config["nfsmount_root"]
            self.localRoot = config["local_root"]  # add by cuilei, May 2016
            self.vpnClient = config["openvpn_client"]
            self.vpnClient2 = config["hicloud-vpn_client"]
            self.vpnprogram = config["hicloud-vpn_program"]
            self.tmp = config["tmp"]       #vlan信息存放在self.tmp VM文件中
            self.hypervisor = config["hypervisor"]
            self.dns = config["dns"]
            os.putenv("PATH", '%s:%s/vmc' % (os.getenv("PATH"), config["script_dir"]))
            socket.setdefaulttimeout(300)
            self.script_dir = config["script_dir"]
            self.portal = config["portal_url"]
            self.openvswitch = Openvswitch()
	    print "init a Openvswitch in ServerClass"
            #os.system("modprobe nbd max_part=8")
            print "init a ServerClass"
        except BaseException as e:
            logger.error('************** ServerClass __init__ is error: %s ****************' % repr(e))

            # 暂停虚拟机

    def pauseSVM(self, uuid):
        logger.info('***** pauseSVM is running *****')
        conn = libvirt.open(None)
        if conn == None:
            logger.error('Failed to open connection to the hypervisor')
            return LibvirtOffErr

        try:
            dom = conn.lookupByUUIDString(uuid)
            dom.suspend()
            logger.info("succed to suspend vm %s" % uuid)
	    conn.close()
            return 0
        except libvirt.libvirtError:
            logger.error("dom do not exist")
            return HibernateVMErr

    def resumeSVM(self, uuid):
        logger.info('***** resumeSVM is running *****')
        conn = libvirt.open(None)
        if conn == None:
            logger.error('Failed to open connection to the hypervisor')
            return LibvirtOffErr

        try:
            dom = conn.lookupByUUIDString(uuid)
            dom.resume()
            logger.info("succed to resume vm %s" % uuid)
            conn.close()
            return 0
        except libvirt.libvirtError:
            logger.error("dom do not exist")
            return HibernateVMErr

    # 创建虚拟机快照
    def snapshotSVM(self, uuid, snapshot_name):
        logger.info('***** snapshotSVM is running *****')
        xmldesc = '<?xml version="1.0" ?>\
            <domainsnapshot>\
            <name>%s</name>\
            <description>Snapshot of OS</description>\
            <domain>\
                <uuid>%s</uuid>\
            </domain>\
            </domainsnapshot>' % (snapshot_name, uuid)

        logger.info('snapshot xml: %s' % xmldesc)
        conn = libvirt.open('qemu:///system')
        if conn == None:
            logger.error("Failed to open connection to the hypervisor")
            return LibvirtOffErr

        try:
            dom = conn.lookupByUUIDString(uuid)
            # 生成快照
            snapshot_dom = dom.snapshotCreateXML(xmldesc.encode("utf-8"), 0)

            if snapshot_dom == None:
                logger.error("Failed to snapshot vm %s", uuid)
            else:
                logger.info("Succeed to snapshot vm %s", uuid)
            return 0
        except Exception as e:
            logger.error("snapshot vm error: %s", e)
            return OtherException
        finally:
            conn.close()

    # 删除虚拟机快照
    def deletesnapshotSVM(self, uuid, snapshot_name):
        logger.info('***** deletesnapshotSVM is running *****')

        conn = libvirt.open('qemu:///system')
        if conn == None:
            logger.error("Failed to open connection to the hypervisor")
            return LibvirtOffErr

        try:
            dom = conn.lookupByUUIDString(uuid)
            snapshot = dom.snapshotLookupByName(snapshot_name.encode("utf-8"), 0)
            rtn = snapshot.delete(0)
            if rtn != 0:
                logger.error("Failed to delete snapshot vm %s", uuid)
                return OtherException
            else:
                return 0
        except Exception as e:
            logger.error("delete snapshot vm error: %s", e)
        finally:
            conn.close()

    def hastart(self, cluster):
        logger.info('***** hastart is running *****')
        try:
            self.hastop(cluster)  # 停止已有进程
            if not daemonize():
                tmp = os.path.split(os.path.realpath(__file__))[0]
                program = '%s/HACheck.pyc' % tmp if os.path.exists('%s/HACheck.pyc' % tmp) else '%s/HACheck.py' % tmp
                cmd = 'python %s %s &' % (program, cluster)
                os.system(cmd)  # 启动进程
            logger.info("succeed to start HA feature!")
        except Exception as e:
            logger.error("hastart error: %s", e)
        return 0

    def hastop(self, cluster):
        logger.info('***** hastop is running *****')
        try:
            tmp = exe_timeout_command("ps aux|grep HACheck.py")
            for line in tmp:
                if 'python %s/HACheck.py' % os.path.split(os.path.realpath(__file__))[0] in line:
                    exe_timeout_command('kill %s' % line.split()[1])  # 杀死已有进程
            logger.info("succeed to stop HA feature!")
        except Exception as e:
            logger.error("hastop error: %s", e)
        return 0

    # ****************************************************************************************************************#
    # 停止虚拟机
    def stopSVM(self, uuid):
        logger.info('***** stopSVM is running *****')
        conn = libvirt.open(None)
        if conn == None:
            logger.error('Failed to open connection to the hypervisor')
            return -1
        try:
            dom = conn.lookupByUUIDString(uuid)
            name = dom.name()
            ret = 0
            ret = dom.destroy()
            if ret != 0:
                logger.error("Failed to shutdown vm %s", name)
                return -1
            else:
                logger.info("Succeed to shutdown vm %s", name)
        	return 0
        except Exception as e:
            logger.error("VM does't exist:%s"%(str(e)))
            return -1

    # reboot VMI
    def rebootSVM(self, uuid):
        logger.info('***** rebootSVM is running *****')
        conn = libvirt.open(None)
        if conn == None:
            logger.error('Failed to open connection to the hypervisor')
            return -1
        try:
            dom = conn.lookupByUUIDString(uuid)
            name = dom.name()
            ret = dom.reboot()
            if ret != 0:
                logger.error("Failed to reboot vm %s", name)
                return -1
            else:
                logger.info("Succeed to reboot vm %s", name)
                return 0
        except libvirt.libvirtError as e:
            logger.error("VM does't exist!")
            return -1

    def infoSVM(self, uuid):
        logger.info("infoSVM is running")
        try:
                info_list = []
                host_address = get_vmc_address()
                info_list.append(host_address)
                ret = self.checkSVM(uuid)
    		if ret!=0:
			return []            
                ret = self.openvswitch.exeCmd("echo 123456 | sudo -S virsh dumpxml %s | grep vnc"%(str(uuid)))
                if ret[0]!=0:
                        self.logger.info("get %s vnc_ port: %s"%(str(uuid), str(ret[1])))
                        return []
                vnc_port = re.search("([0-9][0-9][0-9][0-9]|-1)",re.search( "port=\'[0-9|-]*\'", ret[1]).group(0)).group(0)
                info_list.append(vnc_port)
                info_list.append(uuid)
                ret = self.openvswitch.exeCmd("echo 123456 | sudo -S virsh dumpxml %s"%(str(uuid)))
                if ret[0]!=0:
                        self.logger.info("get %s tap_list: %s"%(str(uuid), str(ret[1])))
                        return []
                tapList = re.findall("tap[^\']*", ret[1])
                for i in range(0, len(tapList)):
                        info_list.append(tapList[i])
                return info_list
	except Exception as err:
                logger.error("infoSVM error: %s"%(str(err)))
                return []

    def listSVMs(self):
	logger.info("listSVMs is running")
	try:
		ret = commands.getstatusoutput("echo 123456 | sudo -S virsh list --all")
		if ret[0]==0:
			return ret[1]
		else:
			return None		
	except Exception as err:
		logger.error("listSVMs error: %s"%(str(err)))
		return None
    # ****************************************************************************************************************#
    # 将存储显示方式改为字节
    def parse_size(self, entity):
        logger.info('***** parse_size is running *****')
        try:
            entity = entity.strip()
            logger.info('entity value: %s' % entity)
            entity = entity.lower()
            if not entity.isdigit():
                if entity[-1] == 'g':
                    entity = int(entity[0:len(entity) - 1]) * 1024 * 1024 * 1024
                elif entity[-1] == 'm':
                    entity = int(entity[0:len(entity) - 1]) * 1024 * 1024
                else:
                    entity = int(entity[0:-1]) * 1024  # no use
            else:
                entity = int(entity) * 1024 * 1024 * 1024
            entity = str(entity)
            logger.info("size is %s" % entity)
            return entity
        except Exception as e:
            logger.error('parse_size is error: %s' % repr(e))
            return None

    def generate_firewall_xml(self, uuid, path):
	logger.info("generate_firewall_xml is running")
	try:
		if os.path.exists("/vmc160/firewall.xml") != 1:
			logger.error("source firewall xml file doesn't exist")
			return -1
		ret = commands.getstatusoutput('echo 123456 | sudo -S cp /vmc160/firewall.xml %s'%(str(path)))
		logger.debug("execute this cmd result:%s"%(ret[0]))
		if ret[0]!=0:
			return -1
		return 0
	except Exception as e:
		logger.error("generate_firewall_xml error:%s"%(str(e)))
		return -1

    #生成处理虚拟机模板   ###boot from isp, have iso path
    def generate_vm_xml(self, uuid, path):    
        if os.path.exists(path) != 1:
            os.system("touch %s"%path)

        xml = "<domain type='kvm'>\n\
<name>1234-test3</name>\n\
<uuid>6045eb6c-6f47-11e0-ab45-78e7d158fd70</uuid>\n\
<os>\n\
        <type >hvm</type>\n\
        <boot dev='hd'/>\n\
        <boot dev='cdrom'/>\n\
        <bootmenu enable='yes'/>\n\
</os>\n\
<features><pae/><acpi/><apic/></features>\n\
<on_poweroff>destroy</on_poweroff>\n\
<on_reboot>restart</on_reboot>\n\
<on_crash>destroy</on_crash>\n\
<clock offset='utc'/>\n\
<memory>1048576</memory>\n\
<currentMemory>1048576</currentMemory>\n\
<vcpu>1</vcpu>\n\
<bootScript>\n\
</bootScript>\n\
<shutdownScript>\n\
</shutdownScript>\n\
<devices>\n\
<input type='tablet' bus='usb'/>\n\
<disk type='file' device='disk'>\n\
        <driver name='qemu' type='qcow2' />\n\
        <source file='/vmc160/1234-test3.img'/>\n\
        <target dev='vda' bus='virtio'/>\n\
</disk>\n\
<disk device='cdrom' type='file'>\n\
    <source file='/vmc160/ubuntu16a.iso'/>\n\
    <target bus='ide' dev='hdc'/>\n\
</disk>\n\
<graphics type='vnc'  port='-1'  listen='0.0.0.0'/>\n\
<interface type='ethernet'>\n\
    <mac address='52:54:00:dc:f4:c2'/>\n\
    <target dev='tap1111'/>\n\
    <model type='virtio'/>\n\
</interface>\n\
</devices>\n\
</domain>"
        f = None
        try:
            f = open(path, 'w')
            f.write(xml)
        except Exception as err:
            raise Exception(err)
        finally:
            if f != None:
                f.close()

    # 生成处理虚拟机模板  ###boot from disk, no iso path
    def generate_vm_xml_config(self, uuid, path):
        if os.path.exists(path) != 1:
            os.system("touch %s"%path)

        xml = "<domain type='kvm'>\n\
<name>1234-test3</name>\n\
<uuid>6045eb6c-6f47-11e0-ab45-78e7d158fd70</uuid>\n\
<os>\n\
        <type >hvm</type>\n\
        <boot dev='hd'/>\n\
        <bootmenu enable='yes'/>\n\
</os>\n\
<features><pae/><acpi/><apic/></features>\n\
<on_poweroff>destroy</on_poweroff>\n\
<on_reboot>restart</on_reboot>\n\
<on_crash>destroy</on_crash>\n\
<clock offset='utc'/>\n\
<memory>1048576</memory>\n\
<currentMemory>1048576</currentMemory>\n\
<vcpu>1</vcpu>\n\
<bootScript>\n\
</bootScript>\n\
<shutdownScript>\n\
</shutdownScript>\n\
<devices>\n\
<input type='tablet' bus='usb'/>\n\
<disk type='file' device='disk'>\n\
        <driver name='qemu' type='qcow2' />\n\
        <source file='/vmc160/1234-test3.img'/>\n\
        <target dev='vda' bus='virtio'/>\n\
</disk>\n\
<graphics type='vnc'  port='-1'  listen='0.0.0.0'/>\n\
<interface type='ethernet'>\n\
    <mac address='52:54:00:dc:f4:c2'/>\n\
    <target dev='tap1111'/>\n\
    <model type='virtio'/>\n\
</interface>\n\
</devices>\n\
</domain>"

        f = None
        try:
            f = open(path, 'w')
            f.write(xml)
        except Exception as err:
            raise Exception(err)
        finally:
            if f != None:
                f.close()

    # 挂载存储
    # vstore_address, vstore_path
    # local_ip, local_vstore_path
    def __mount_store_dir(self, vstore_address, vstore_path, old_vstore_address=None):
        logger.info('***** __mount_store_dir is running *****')
        # 获取本地主机对应的ip地址(172.20.0.234)
        local_ip = get_vmc_address()

        try:
            remote_store_path = '%s:%s' % (vstore_address, vstore_path)
            address_md5 = None
            address2md5 = None  # get_address_md5() # add by cuilei
            # 本地地址使用md5值
            if address2md5 is not None and address2md5.has_key(vstore_address):
                address_md5 = address2md5[vstore_address]
                local_store_path = '%s/%s' % (self.nfsmountRoot, address_md5)
                old_umount_path = local_store_path
            else:   ###############################
		###local_store_path:/tmp/adtp-master/hicloud/rootDir/nfsmountRoot/vstore_address
                local_store_path = '%s/%s' % (self.nfsmountRoot, vstore_address)
                if old_vstore_address is not None:
                    old_umount_path = '%s/%s' % (self.nfsmountRoot, old_vstore_address)
                else:       #################      
                    old_umount_path = None

            logger.info('old_umount_path value: %s' % old_umount_path)
            # 删除旧的链接文件或挂载点
            if old_umount_path is not None:
                os.system('umount -l %s' % old_umount_path)

            if not os.path.exists(local_store_path):     ################建立local_store_path目录
                os.system('mkdir -p %s' % local_store_path)

            logger.info('local_ip: %s, vstore_address: %s, local_store_path: %s, remote_store_path: %s' % (
                repr(local_ip), vstore_address, local_store_path, remote_store_path))
            if local_ip is not None and vstore_address.strip() != local_ip:   #############远程存储机器IP不是本机IP，虚拟存储挂载到远程机器
                is_mount_store = False
                check_mount_cmd = 'mount | grep %s' % remote_store_path
                logger.info("check mount path: %s " % check_mount_cmd)
                check_result = commands.getstatusoutput(check_mount_cmd)
                logger.info('check result: %s' % str(check_result))
                if check_result[0] != 0:   ####没有挂载，需要重新挂载
                    is_mount_store = True
                else:
                    check_mount_info = check_result[1].split('type')[0].strip()
                    current_mount_info = '%s on %s' % (remote_store_path, local_store_path)
                    logger.info('result mount: %s, current mount: %s' % (check_mount_info, current_mount_info))
                    if check_mount_info != current_mount_info:
                        # 取消主机已有的挂载
                        umount_cmd = 'umount -l %s' % check_mount_info.split('on')[1].strip()
                        logger.info('umount cmd: %s' % umount_cmd)
                        umount_result = commands.getstatusoutput(umount_cmd)
                        if umount_result[0] != 0:
                            logger.info('umount %s is error !' % local_store_path)
                        is_mount_store = True

                if is_mount_store:
                    mount_times = 1
                    # 进行最多5次mount操作，直到mount成功
		    # 把remote_store_path挂载到local_store_path
                    while mount_times <= 5:
                        try:
                            mount_cmd = 'mount -t nfs %s %s' % (remote_store_path, local_store_path)
                            logger.info('mount times: %s, execute mount: %s' % (mount_times, mount_cmd))
                            mount_result = commands.getstatusoutput(mount_cmd)
                            if mount_result[0] != 0:
                                logger.info('execute mount is failed: %s, error: %s' % (mount_cmd, mount_result[1]))
                                time.sleep(5)
                            else:
                                # mount成功，结束循环
                                break
                        except Exception as e:
                            logger.error('nfs server is error: %s' % repr(e))
                            break
                            return
                        finally:
                            mount_times += 1
            else:    ###虚拟存储挂载到本机,vstore_path是源目录
                logger.info('vstore_path value: %s, local_store_path value: %s' % (vstore_path, local_store_path))
                if os.path.exists(local_store_path):
                    if os.path.ismount(local_store_path):  #####local_store_path是否是挂载点
                        commands.getstatusoutput('umount -l %s' % local_store_path)
                    elif not os.path.islink(local_store_path):
                        cp_cmd = 'cp -a %s/* %s' % (local_store_path, vstore_path)
                        logger.info('cp_cmd value: %s' % cp_cmd)
                        # 将链接点内容拷贝到源目录中
                        commands.getstatusoutput(cp_cmd)

                    # 删除本地链接
                    os.system('rm -rf %s' % local_store_path)
                    os.system('rm -rf %s/%s' % (self.nfsmountRoot, local_ip))

                if vstore_path[0] != '/':
                    vstore_path = '/%s' % vstore_path
                ln_cmd = 'ln -sf %s %s' % (vstore_path, local_store_path)
                logger.info('ln_cmd value is: %s' % ln_cmd)
                try:
                    ln_reslut = commands.getstatusoutput(ln_cmd)
                except Exception as e:
                    logger.error('execute local ln is error: %s' % repr(e))
                    return
            # 在存储中创建三个文件夹：nfsbase(存放模板的img)、nfscow(存放虚拟机的img)、template(存放模板的配置文件)
            for mount_dir in (
                    '%s/nfsbase' % local_store_path, '%s/nfscow' % local_store_path, '%s/template' % local_store_path):
                if not os.path.exists(mount_dir):
                    os.system('mkdir -p %s' % mount_dir)
            #os.system('hicloud-monitor')
            logger.info('__mount_store_dir is finished !')
        except Exception as e:
            logger.error('__mount_store_dir is error: %s' % repr(e))

    # 创建镜像文件
    def __create_img(self, disk_size, img_path):
        logger.info('***** __create_img is running *****')
        # 转换为以KB为单位
        disk_size = self.parse_size(disk_size)
        disk_size = "40"
	img_path_dir = img_path.rsplit('/',1)[0]	
	if os.path.exists(img_path_dir)!=1:
	    os.system('mkdir -p %s' % img_path_dir)
	logger.info("img目录:%s"%img_path_dir)
        if self.hypervisor == 'kvm':   ###################
            if os.path.exists(img_path)!=1:
            	logger.info("Create vm img, hypervisor is kvm")
            	cmd = "qemu-img create %s -f qcow2 %sG" % (img_path, disk_size)
            	logger.info("create vm cmd: %s" % cmd)
            	try:
                	ret = commands.getstatusoutput(cmd)
                	if ret[0] != 0:
                    		logger.error("Create vm disk error.")
                   	return CreateVMError
            	except Exception as err:
                	return CreateVMError
	    else:
                logger.info("%s has been created"%img_path)
        elif self.hypervisor == 'xen':
            logger.info("Create vm img, hypervisor is xen")
            return CreateVMError
        else:
            logger.error("Create vm img, unknown hypervisor %s" % self.hypervisor)
            return CreateVMError
        return 0

    def create_img_by_vmi(self, original_img_path, target_img_path):
        logger.info('***** create_img_by_vmi_local is running *****')
        logger.info('original_img_path value: %s, target_img_path value: %s' % (original_img_path, target_img_path))
        if not os.path.exists(target_img_path) and os.path.exists(original_img_path):
            create_command = "echo 123456 | sudo -S cp %s %s" % (original_img_path, target_img_path)
            logger.info('create vmi img local: %s' % create_command)
            status_output = commands.getstatusoutput(create_command)
            logger.info('create vmi img local result: %s' % status_output[0])
            if status_output[0] != 0:
                logger.error("when copy image is error: %s" % status_output[1])
 
    def random_mac(self):
        logger.info("random_mac is running")
        Maclist = []
        for i in range(1,7):
            RANDSTR = "".join(random.sample("0123456789abcdef",2))
            Maclist.append(RANDSTR)
        randMac = ":".join(Maclist)
        return randMac

    def __create_firewall_xml(self, fwl_uuid, uuid, tap_list, mac_list):
	logger.info("__create_firewall_xml is running")
	try:
		vm_xml_path = '/vmc160/firewall_'+str(uuid)+'.xml'	
		if self.generate_firewall_xml(uuid, vm_xml_path)!=0:
			return -1
		doc = minidom.parse(vm_xml_path)
		tags = ['uuid', 'name']
		paras = [str(fwl_uuid), 'firewall_'+str(uuid)]
		for i in range(0, len(tags)):
			item = doc.childNodes[0].getElementsByTagName(tags[i])[0]
                	item.childNodes[0].data = paras[i]  # set new value
		devices_doc = doc.childNodes[0].getElementsByTagName('devices')[0]
                interface_docs = devices_doc.getElementsByTagName('interface')
		disk_docs = devices_doc.getElementsByTagName('disk')
		disk_doc = disk_docs[0]
		vm_img_path = '/vmc160/firewall_'+str(uuid)+'.img'
		disk_doc.getElementsByTagName('source')[0].setAttribute('file', vm_img_path)
		i = 0
		for interface_doc in interface_docs:
			interface_doc.getElementsByTagName('target')[0].setAttribute('dev', str(tap_list[i]))
			interface_doc.getElementsByTagName('mac')[0].setAttribute('address', str(mac_list[i]))
			i = i + 1
		self.create_img_by_vmi('/vmc160/firewall.img', '/vmc160/firewall_%s.img'%(str(uuid)))
		ret = saveXml2File(doc.toxml(), '/vmc160', vm_xml_path)
		if ret != 0:
			return -1
		return 0
	except Exception as e:
		logger.error("__create_firewall_xml error:%s"%(str(e)))
		return -1
 
    def __create_vm_xml(self, uuid, name, mem_size, local_vmc_xml_path, vm_xml_path, img_path, iso_path, networkSources, cpu_cnt, os_name, os_version, tap_name, flags):
        logger.info('***** __create_vm_xml is running *****')
        try:
            logger.info(vm_xml_path)
            if (iso_path.strip() == 'HMI') or (iso_path.strip() == "PLC") or (iso_path.strip() == 'Unity') or (iso_path.strip() == "AD"):  #this is software_type, iso_path is null, imply it is configured
                self.generate_vm_xml_config(uuid, vm_xml_path)
            else:
                self.generate_vm_xml(uuid, vm_xml_path)

            doc = minidom.parse(vm_xml_path)
            tags = ['uuid', 'name', 'memory', 'currentMemory', 'vcpu']
            paras = [uuid, name, mem_size, mem_size, cpu_cnt]
            for i in range(len(tags)):
                item = doc.childNodes[0].getElementsByTagName(tags[i])[0]
                logger.info(tags[i])
                logger.info(paras[i])
                logger.info(item.childNodes[0].data)
                item.childNodes[0].data = paras[i]  # set new value

            # 获取iso的存储地址
	    if (iso_path.strip() != "PLC") and (iso_path.strip() != "HMI") and (iso_path.strip() != "Unity") and (iso_path.strip() != "AD"):
            	iso_path = filter_address(iso_path)
            	logger.info('iso_path: %s, img_path: %s' % (iso_path, img_path))
            	disks = doc.getElementsByTagName('disk')
            	for disk in disks:
                	disk_device = disk.getAttribute('device').strip()
                	logger.info('disk device: %s' % disk_device)
                	if disk_device == 'cdrom':
                    		if iso_path.strip() != '':
                        		disk.getElementsByTagName('source')[0].setAttribute('file', iso_path)
                	elif disk_device == 'disk':
                    		disk.getElementsByTagName('source')[0].setAttribute('file', img_path)
	    else:
		software_type = iso_path
		source_img_path = "/vmc160/"+os_name+"_"+os_version+"_"+software_type+".img"
		target_img_path = source_img_path #"/vmc160/"+str(uuid)+".img"
		if os.path.exists(source_img_path):
			#self.create_img_by_vmi(source_img_path, target_img_path)
			disk = doc.getElementsByTagName('disk')[0]
			disk.getElementsByTagName('source')[0].setAttribute('file', target_img_path)
		else:
			if not os.path.exists(source_img_path):
				logger.error("source image doesn't exist")
			else:
				logger.info("target image has been created")

            # add nic configruation
            devices_doc = doc.childNodes[0].getElementsByTagName('devices')[0]
            interface_doc = devices_doc.getElementsByTagName('interface')[0]
            #tap_name = get_first_tap_name(uuid)
            logger.info(len(networkSources))
            for i in range(len(networkSources)):
                mac = networkSources[i].getElementsByTagName("MAC")[0].firstChild.data
                logger.info("MAC(1): %s", mac)
                if i == 0:
                    interface_doc.getElementsByTagName('target')[0].setAttribute('dev', tap_name)
                    interface_doc.getElementsByTagName('mac')[0].setAttribute('address', mac)
                else:
                    # cloneNode(deep) deep表示拷贝的深度，克隆的根节点深度是0
                    next_interface_doc = interface_doc.cloneNode(2)
                    next_interface_doc.getElementsByTagName('target')[0].setAttribute('dev', tap_name)
                    next_interface_doc.getElementsByTagName('mac')[0].setAttribute('address', mac)
                    devices_doc.appendChild(next_interface_doc)
                # 生成一个虚拟网卡节点
                tap_name = get_next_tap_name(tap_name)
	    if flags == "U":
		tap_name = 'tap_less'
                mac = '52:54:00:dc:e5:f9'
		next_interface_doc = interface_doc.cloneNode(2)
                next_interface_doc.getElementsByTagName('target')[0].setAttribute('dev', tap_name)
                next_interface_doc.getElementsByTagName('mac')[0].setAttribute('address', mac)
                devices_doc.appendChild(next_interface_doc)
            logger.info("dom.toXml: %s" % doc.toxml())
            logger.info(vm_xml_path)
            logger.info(local_vmc_xml_path)
            # save modified xml
            ret = saveXml2File(doc.toxml(), local_vmc_xml_path, vm_xml_path)  # modify by dy change toXml as toxml
            if ret != 0:
                logger.error("Creating VM ... Failed")
                return CreateVMError
	    
            conn = libvirt.open(None)
            if conn == None:
                logger.error('Failed to open connection to the hypervisor')
                return LibvirtOffErr  # return -4;
            logger.info("Open connection to the hypervisor")

            try:
		logger.info("create the domain %s"%str(uuid))
                conn.defineXML(doc.toxml().encode("utf-8"))
            except Exception as e:
                logger.error('__create_vm_xml define error: %s' % repr(e))
            finally:
                conn.close()
            
            logger.info("TEMP: save vm xml is ok")
	    return 0
        except Exception as e:
            logger.info("TEMP: create vm xml ERROR: %s" % repr(e))
            return -1

    # 使用iso创建虚拟机
    '''
    def createSVM(self, uuid, xml):
	try:
            # 获取虚拟机基本信息
	    logger.info("虚拟机基本信息:%s\n",xml)
            name, desc, mem_size, disk_size, cpu_cnt, nic_cnt, passwd, vstore_ip, os_name, os_version, sub_vstore_path, iso_path, storage_type = getBasicInfo(xml)
            mem_size = str(int(float(mem_size)) * 1024)
	    deploy_path = storage_type
            # write vlan info to local file
            vlans = getVlanNetworkSource(xml)
	    ###configuration file of vlan:self.tmp+VM+VMI+uuid 
            self.setVlan(uuid, repr(vlans))  # add by cuilei, May 2016
    	    logger.info("将虚拟机VLAN信息写入文件: %s", self.tmp+VM+"/"+str(uuid))       
	    logger.info("vstore_ip: %s, sub_vstore_ip: %s"%(vstore_ip, sub_vstore_path))
	 
	    vmc_address = get_vmc_address()
	    
            temp_vmi_info_path = filter_address('%s/%s/%s_import_vmi_info.txt' % (self.nfsmountRoot, vmc_address, str(uuid)),
                                                vmc_address)
            update_vmi_info(uuid, temp_vmi_info_path, xml)   ###虚拟机信息存储在self.nfsmountRoot/vmc_address/"uuid"_import_vmi_info.txt中
	    logger.info("将虚拟机信息写入文件：%s", temp_vmi_info_path)
	                
	    # self.local = /tmp/adtp-master/hicloud/rootDir/localRoot
            if deploy_path == "nfs":
		vmc_path = filter_address('%s/%s'%(self.nfsmount, vstore_ip), vstore_ip)
                img_path = "/vmc160/%.img"%(uuid)    ###"%s/nfscow/%.img"%(vmc_path, uuid)
	    elif deploy_path == "local":
                vmc_path = self.localRoot
                img_path = "/vmc160/%.img"%(uuid)    ###'%s/cow/%s.img' % (vmc_path, uuid)
	    #创建基础镜像
	    
            result = self.__create_img(disk_size, img_path)
            logger.info("创建img文件到路径: %s", img_path)
	    networkSources = minidom.parseString(xml.encode("utf-8")).getElementsByTagName("NIC")

	    logger.info("虚拟机NIC信息:%s\n", networkSources)
            # fix bug: 'unknown OS type hvm'
            if exe_timeout_command('virsh capabilities') is None:
                logger.info("virsh capabilities is failed!")

            vm_xml_path = '%s/%s.xml' % (self.vmxmlRoot, uuid)
            result = self.__create_vm_xml(uuid, name, mem_size, self.vmxmlRoot, vm_xml_path, img_path, iso_path,
                                          networkSources, int(cpu_cnt), os_name, os_version)
            logger.info("将虚拟机信息写入文件: %s", vm_xml_path)
            logger.info("Create virtual machine from ISO over")
            return 0
            
        except Exception as err:
            logger.error("Create virtual machine from ISO error: %s" % str(err))
            return -1
    
    def func2(self, uuid, xml):
	return xml+str(uuid)
    ''' 

    ###从image创建虚拟机
    def createSVMimage(self, uuid, xml, tap_name, flags):
	logger.info("createSVMimage is running")
        try:
            hostname, desc, mem, disk_size, cpu_cnt, nic_cnt, password, vstore_ip, os_type, os_version, sub_vstore_path, software_type, storage_type = getBasicInfo(xml)
            mem = str(int(float(mem)) * 1024)
            deploy_path = storage_type
            # write vlan info to local file
            vlans = getVlanNetworkSource(xml)
            ###configuration file of vlan:self.tmp+VM+VMI+uuid 
            self.setVlan(uuid, repr(vlans), tap_name)  # add by cuilei, May 2016
            logger.info("write vlan info in: %s", self.tmp+VM+"/"+str(uuid))
            logger.info("vstore_ip: %s, sub_vstore_ip: %s"%(vstore_ip, sub_vstore_path))
            ###we don't need mount function
            '''
            self.__mount_store_dir(vstore_ip, sub_vstore_path)
            '''
            vmc_address = get_vmc_address()

            temp_vmi_info_path = filter_address('%s/%s.txt' % (self.nfsmountRoot, str(uuid)))
            update_vmi_info(uuid, temp_vmi_info_path, xml)   ###虚拟机信息存储在self.nfsmountRoot/vmc_address/"uuid"_import_vmi_info.txt中
            logger.info("将虚拟机信息写入文件：%s", temp_vmi_info_path)

            # self.local = /tmp/adtp-master/hicloud/rootDir/localRoot
            
            networkSources = minidom.parseString(xml.encode("utf-8")).getElementsByTagName("NIC")

            logger.info("虚拟机NIC信息:%s\n", networkSources)
            # fix bug: 'unknown OS type hvm'
            if exe_timeout_command('virsh capabilities') is None:
		logger.info("virsh capabilities is failed!")

            vm_xml_path = '%s/%s.xml' % (self.vmxmlRoot, uuid)
	    img_path = "/vmc160/backups.img"
            result = self.__create_vm_xml(uuid, hostname, mem, self.vmxmlRoot, vm_xml_path, img_path, software_type, networkSources, int(cpu_cnt), os_type, os_version, tap_name, flags)
            logger.info("store xml in path: %s", vm_xml_path)
            logger.info("Create virtual machine from ISO over")
	    res = str(vmc_address) + " " + str(hostname) 
            return res

        except Exception as err:
            logger.error("Create virtual machine from image error: %s" % str(err))
            return " "

    # 使用模板创建虚拟机

    # write the tap created to uuid.xml
    def __write_tap_to_xml(self, tap, uuid):
        logger.info('***** __write_tap_to_xml is running *****')
        xml_path = '%s/%s.xml' % (self.vmxmlRoot, uuid)
        if not os.path.exists(xml_path):
            logger.error("Xml %s doesn't exist" % (xml_path))
            return -1
        dom = minidom.parse(xml_path)
        dom.getElementsByTagName("interface")[0].getElementsByTagName("target")[0].attributes["dev"].value = tap
        f = open(xml_path, 'w')
        logger.debug("Write tap into xml")
        f.write(dom.toxml())
        f.close()
        return dom.toxml()

    # 添加虚拟机网络信息
    def __create_interface_to_xml(self, tap_name, xml_desc):
        logger.info('***** __create_interface_to_xml is running *****')
        try:
            interfaceDevice = xml_desc.createElement('interface')
            interfaceDevice.setAttribute('type', 'ethernet')
            tap_item = xml_desc.createElement('target')
            tap_item.setAttribute('dev', tap_name)

            model_item = xml_desc.createElement('model')
            # model_item.setAttribute('type', 'virtio') # TODO: virtio need driver
            model_item.setAttribute('type', 'rtl8139')  # TODO: virtio need driver

            script_item = xml_desc.createElement('script')
            script_item.setAttribute('path', 'no')

            interfaceDevice.appendChild(tap_item)
            interfaceDevice.appendChild(model_item)
            interfaceDevice.appendChild(script_item)
            return interfaceDevice
        except Exception as err:
            logger.error("Create interface error: %s" % str(err))
            return -1

    def __add_disk_to_xml(self, xml_desc, disk_path, os_type):
        logger.info('***** __add_disk_to_xml is running *****')
        try:
            disks = xml_desc.getElementsByTagName("disk")
            if len(disks) == 0:
                return -1
            dev_item = xml_desc.getElementsByTagName('devices')[0]
            # 创建一个新的磁盘信息
            disk = xml_desc.createElement('disk')
            disk.setAttribute('type', 'file')
            disk.setAttribute('device', 'disk')

            diskdrive = xml_desc.createElement('driver')
            diskdrive.setAttribute('name', 'qemu')
            diskdrive.setAttribute('type', 'qcow2')

            extended_source = xml_desc.createElement('source')
            # 将镜像文件存储路径加入模板
            extended_source.setAttribute('file', disk_path)

            # 设置磁盘驱动类型
            target = xml_desc.createElement('target')
            # if os_type.find("windows") == -1:
            #    target.setAttribute('bus', 'virtio')
            # else:
            target.setAttribute('bus', 'ide')
            # 获取最后一个<disk>下的第一个<target bus="ide" dev="hdc"/>属性dev的值
            latest_dev_name = disks[len(disks) - 1].getElementsByTagName("target")[0].attributes["dev"].value
            # 获取dev属性值最后一个字母ascii码的下一个值对应的字母
            dev_name = latest_dev_name[0:-1] + chr(ord(latest_dev_name[-1]) + 1)  # get next bus device
            target.setAttribute('dev', dev_name)

            disk.appendChild(diskdrive)
            disk.appendChild(extended_source)
            disk.appendChild(target)
            dev_item.appendChild(disk)
            return xml_desc
        except Exception as err:
            logger.error("Add disk to xml error: %s" % str(err))
            return -1

    def __sleep(self):
        time.sleep(0.1)

    # 启动虚拟机
    def startSVM(self, uuid):
        logger.info(str(uuid))
        logger.info('***** startSVM is running *****')
        try:
            conn = libvirt.open(None)
            if conn == None:
                logger.error('Failed to open connection to the hypervisor')
                return LibvirtOffErr
            logger.info("Open connection to the hypervisor")
            logger.info(str(conn.listDomainsID()))

            try:
                dom = conn.lookupByUUIDString(str(uuid))
                logger.info(str(dom.info()))
            except Exception as e:
                xmlFilename = '%s/%s.xml' % (self.vmxmlRoot, uuid.strip())
                logger.info(xmlFilename)
                os.system("echo 123456 | sudo -S virsh define %s" % xmlFilename)
                dom = conn.defineXML(xmlFilename)
                dom = conn.lookupByUUIDString(str(uuid))
                if dom == None:
                    logger.error("Define vm %s failed" % uuid)
                    return -4
            try:
                ret = dom.create()  # Launch a defined domain
                if ret != 0:
                    logger.error("Start vm failed")
                    return -4
                else:
                    logger.info("Starting domain %s ... OK", uuid)
                    time.sleep(0.5)
                    logger.info("hicloud-monitor")
                    os.system("hicloud-monitor")
                    logger.info("Start vm successfully!")
                    self.__sleep()

                    return 0
            except Exception as err:
                logger.error("Start vm error: %s" % str(err))
                return -4
            finally:
                conn.close()
        except Exception as err:
            logger.error("Start vm error: %s" % str(err))
            return -4

    # 合并新添加的磁盘空间
    def __expanded_disk_space(self, old_xml_desc, add_disk_img):
        logger.info('***** __expanded_disk_space is running *****')
        disks = old_xml_desc.getElementsByTagName("disk")
        add_disk_raw_path = '%s_raw.img' % add_disk_img[0: -4]
        logger.info(add_disk_img)
        logger.info(add_disk_raw_path)

        # 删除磁盘添加的raw文件
        if os.path.exists(add_disk_raw_path):
            os.remove(add_disk_raw_path)

        add_convert_raw_cmd = 'kvm-img convert -f qcow2 %s -O raw %s' % (add_disk_img, add_disk_raw_path)
        try:
            logger.info('execute: %s' % add_convert_raw_cmd)
            result = commands.getstatusoutput(add_convert_raw_cmd)
            logger.info('execute result: %s' % result[0])
        except Exception as e:
            logger.error('add img convert to raw is error: %s' % repr(e))
            return

        # 获取最原始镜像文件
        old_img = disks[0].getElementsByTagName('source')[0].getAttribute('file')
        old_disk_raw_path = '%s_raw.img' % old_img[0: -4]
        # 删除磁盘添加的raw文件
        if os.path.exists(old_disk_raw_path):
            os.remove(old_disk_raw_path)

        logger.info(old_disk_raw_path)
        old_convert_raw_cmd = 'kvm-img convert -f qcow2 %s -O raw %s' % (old_img, old_disk_raw_path)
        try:
            logger.info('execute: %s' % old_convert_raw_cmd)
            result = commands.getstatusoutput(old_convert_raw_cmd)
            logger.info('execute result: %s' % result[0])
        except Exception as e:
            logger.error('ord img convert to raw is error: %s' % repr(e))
            return

        # 合并磁盘空间
        expanded_cmd = 'cat %s >> %s' % (add_disk_raw_path, old_disk_raw_path)
        try:
            logger.info('execute: %s' % expanded_cmd)
            result = commands.getstatusoutput(expanded_cmd)
            logger.info('execute result: %s' % result[0])
        except Exception as e:
            logger.error('merge disk space is error: %s' % repr(e))
            return
        finally:
            # 删除磁盘合并前镜像文件
            if os.path.exists(old_img):
                os.remove(old_img)

            # 删除新增的qcow2镜像文件
            if os.path.exists(add_disk_img):
                os.remove(add_disk_img)

            # 删除新增的raw镜像文件
            if os.path.exists(add_disk_raw_path):
                os.remove(add_disk_raw_path)

        old_convert_qcow2_cmd = 'kvm-img convert -f raw %s -O qcow2 %s' % (old_disk_raw_path, old_img)
        try:
            logger.info('execute: %s' % old_convert_qcow2_cmd)
            result = commands.getstatusoutput(old_convert_qcow2_cmd)
            logger.info('execute result: %s' % result[0])
        except Exception as e:
            logger.error('ord img convert to qcow2 is error: %s' % repr(e))
            return
        finally:
            # 删除合并后的raw镜像文件
            if os.path.exists(old_disk_raw_path):
                os.remove(old_disk_raw_path)

        logger.info('merge disk apace is finished')


    # 获得虚拟机监控信息
    def monitorSVM(self, uuid):
        try:
            os.system("hicloud-monitor")
        except Exception as err:
            logger.error("Monitor information Exception : %s", str(err))
        return 0

    # 验证虚拟机是否可连接
    def checkSVM(self, uuid):
        logger.info('***** checkSVM is running *****')
        try:
            conn = libvirt.open(None)
            if conn == None:
                logger.error('Failed to open connection to the hypervisor')
                return LibvirtOffErr

            try:
                dom = conn.lookupByUUIDString(uuid)  # judge vm exists or not
            except Exception as e:
                # 虚拟机是临时的，这时通过libvirt是找不到的，必须进行实例化
                os.system('virsh define %s/%s.xml' % (self.vmxmlRoot, uuid))
                dom = conn.lookupByUUIDString(uuid)

            if dom == None:
                return LibvirtOffErr
            else:
                return 0
        except Exception as e:
            logger.error('checkSVM is error: %s' % repr(e))
            return -1
        finally:
            conn.close()

    def undeploySVM(self, uuid):
        logger.info('***** undeploySVM is running *****')
        if uuid.strip() == "" or uuid == None:
	    logger.error("wrong uuid")
            return -1

        xmlPath = '%s/%s.xml' % (self.vmxmlRoot, uuid)
        imgPath = '/vmc160/%s.img' % (str(uuid))
        vmiPath = '/vmc160/hicloud/rootDir/nfsmountRoot/%s.txt'%(str(uuid))
	vlanPath = '/vmc160/hicloud/vmc/vlan/vmi/%s'%(str(uuid))

        conn = libvirt.open(None)
        if conn is None:
            logger.error('undeploySVM is error: %s' % repr(e))
            return -1

        try:
            if conn == None:
                logger.error('Failed to open connection to the hypervisor')
                return -1
            logger.info("Open connection to the hypervisor")

            dom = conn.lookupByUUIDString(uuid)
            if dom == None:
                logger.error('Failed to find vm %s' % uuid)
                return -1

            ret = dom.undefine()
            if ret != 0:
                logger.error('Failed to undefine vm %s' % uuid)
                return -1

            paths = [xmlPath, imgPath, vmiPath, vlanPath]
            cmds = ['rm -rf %s*' % str(xmlPath), 'rm -rf %s*' % str(imgPath),'rm -rf %s*' % str(vmiPath),'rm -rf %s*' % str(vlanPath)]
            if os.path.exists(xmlPath):
            	for i in range(0,4):
			cmd = cmds[i]
			path = paths[i]
			if os.path.exists(path):
				ret = commands.getstatusoutput(cmd)
				logger.info("execute %s result: %s"%(str(cmd),str(ret[0])))
            conn.close()
	    return 0
        except Exception as e:
            logger.error('undeploy is error: %s' % str(e))
            return -1

    def checkLicense(self, portal_url):
        return True  # add by cuilei, May 2016
        license = CheckLicense()
        check_result = license.run()
        if check_result in (0, 1):
            # change /etc/hicloud/general.yaml
            if (change_portal_url(portal_url) != 0):
                logger.error('Change portal url in /etc/hicloud/general.ymal fialed')
            return True
        else:
            # 清空汇报地址
            change_portal_url('')
            return False

    # 添加主机
    def addVMC(self, xml_desc):
        # xml_desc是主机表中host_desc字段
        logger.info('***** addVMC is running *****')
        try:
            # add by cuilei, May 2016
            logger.info('add host xml: %s' % xml_desc)
            # 获取添加主机的主机名
            # portal_url, portal_ip = get_basic_info_from_VMC_desc(xml_desc)
            # logger.info('protal_url value: %s, portal_ip value: %s' % (portal_url, portal_ip))

            # change /etc/hosts
            # if portal_ip is not None:
            if False:  # add by cuilei
                try:
                    change_portal_host(portal_url, portal_ip)
                except Exception as e:
                    logger.error('change portal hosts is error: %s' % repr(e))
                    return -1
            # add by cuilei, May 2016, TODO
            # os.system('hicloud-monitor')
            logger.info("add VMC over")
            return 0
            if False:  # add by cuilei
                # if self.checkLicense(portal_url):
                host_dom = minidom.parseString(xml_desc.encode("utf-8"))
                vstores = host_dom.getElementsByTagName('Vstore')
                for vstore in vstores:
                    vstore_ip = vstore.getElementsByTagName("VstoreIp")[0].firstChild.data
                    vstore_path = vstore.getElementsByTagName("VstorePath")[0].firstChild.data
                    logger.info('vstore_ip value: %s, vstore_path value: %s' % (vstore_ip, vstore_path))
                    if vstore_ip.strip() == '' or vstore_path.strip() == '':
                        logger.error('Vstore info is Null')
                        continue

                    try:
                        # 随机等待几秒钟，防止所有vmc同时执行mount操作，多并发有可能会导致nfs崩溃
                        time.sleep(random.randint(1, 10))
                        self.__mount_store_dir(vstore_ip, vstore_path)
                    except Exception as e:
                        logger.error('add vstore mount is error: %s' % repr(e))
                        continue

                logger.debug('hicloud-monitor')
                # 添加主机后进行一次主机信息获取
                os.system('hicloud-monitor')
                return 0
            else:
                return -1
        except Exception as err:
            logger.error('add vmc failed: %s' % repr(err))
            return -1

    # 同步主机上的虚机
    def updateVMC(self, vmc_address, vstore2path, vmc_addresses):
        logger.info("updateVMC over")
        return 0  # add by cuilei, May 2016
        logger.info('***** updateVMC is running ******')
        conn = libvirt.open(None)
        vmi2status = {1: 'running', 2: 'unknown', 3: 'paused', 5: 'stopped'}
        vmc2vmis = {}
        vmc2vmis['vmc_address'] = vmc_address
        vmc2vmis['vmis'] = []
        # 传递过来的是字符串，要把它转换成原型类型数据
        vstore2path = eval(vstore2path)
        vmc_addresses = eval(vmc_addresses)
        report_address = [ip for ip in
                          commands.getstatusoutput("less /etc/hosts | grep -v '^#\|::\|127.0.0.1' | awk '{print $1}'")[
                              1].split('\n') if ip.strip() != '']
        vmc_addresses.extend(report_address)
        vmc_addresses = tuple(set(vmc_addresses))
        daemon_config = Config.load(str('/etc/hicloud/daemon.yaml'))
        listen_port = daemon_config['listen_port']
        vmc_md5_dicts = []
        original2portal2md5 = None
        for address in vmc_addresses:
            try:
                json_file = urllib2.urlopen('http://%s:%s/vmc/md5_address.json' % (address, listen_port))
                vmc_md5_dicts.append(eval(json_file.read()))
                json_file.close()
            except:
                continue

        try:
            domain_names = [item.split()[1] for item in commands.getstatusoutput('virsh list --all')[1].split('\n')[2:]
                            if len(item.strip()) > 0]
            domain_uuids = [conn.lookupByName(domain_name).UUIDString() for domain_name in domain_names if
                            len(domain_name.strip()) > 0]
            if not os.path.exists(self.vmxmlRoot):
                os.mkdir(self.vmxmlRoot)

            # 存在实例，不存在xml
            for domain_uuid in domain_uuids:
                domain_xml = '%s/%s.xml' % (self.vmxmlRoot, domain_uuid)
                if not os.path.exists(domain_xml):
                    domain_xml_file = open(domain_xml, 'w')
                    try:
                        domain = conn.lookupByUUIDString(domain_uuid)
                        domain_xml_file.write(domain.XMLDesc(0))
                    finally:
                        domain_xml_file.close()

            # 解析虚机xml，mount未挂载的存储
            all_domain_names = [item.split()[1] for item in
                                commands.getstatusoutput('virsh list --all')[1].split('\n')[2:] if
                                len(item.strip()) > 0]
            logger.info('domain_names: %s, vmi xml path: %s' % (repr(all_domain_names), '%s/*.xml' % self.vmxmlRoot))
            files = glob.glob('%s/*.xml' % self.vmxmlRoot)
            for vmi_xml_file in files:
                logger.info('vmi_xml_file vlaue: %s' % vmi_xml_file)
                doc = minidom.parse(vmi_xml_file)
                vmi2info = {}
                vmi2info['name'] = doc.getElementsByTagName('name')[0].firstChild.data
                vmi2info['uuid'] = doc.getElementsByTagName('uuid')[0].firstChild.data
                vmi2info['mem_size'] = doc.getElementsByTagName('memory')[0].firstChild.data
                vmi2info['cpu_count'] = doc.getElementsByTagName('vcpu')[0].firstChild.data
                try:
                    domain = conn.lookupByUUIDString(vmi2info['uuid'])
                    vmi2info['status'] = vmi2status[domain.info()[0]]
                    snapshot_names = domain.snapshotListNames(0)
                    snapshot2info = {}
                    for snapshot_name in snapshot_names:
                        try:
                            snapshot = domain.snapshotLookupByName(snapshot_name, 0)
                            snapshot_doc = minidom.parseString(snapshot.getXMLDesc(0))
                            state = snapshot_doc.getElementsByTagName('state')[0].firstChild.data
                            snapshot_parent = snapshot_doc.getElementsByTagName('parent')
                            if len(snapshot_parent) == 0:
                                parent_snapshot_name = None
                            else:
                                parent_snapshot_name = snapshot_parent[0].getElementsByTagName('name')[
                                    0].firstChild.data
                            snapshot2info[snapshot_name] = {'state': state,
                                                            'parent_snapshot_name': parent_snapshot_name}
                        except:
                            continue

                    logger.info('snapshot2info value: %s' % repr(snapshot2info))
                    vmi2info['snapshot2info'] = snapshot2info
                except:
                    os.remove(vmi_xml_file)
                    continue

                if not vstore2path.has_key(vmc_address):
                    continue

                temp_vmi_info_file = filter_address('%s/%s/import_vmi_info.txt' % (self.nfsmountRoot, vmc_address),
                                                    vmc_address)
                if not os.path.exists(temp_vmi_info_file):
                    os.system('touch %s' % temp_vmi_info_file)

                temp_vmi_info = open(temp_vmi_info_file, 'r')
                temp_vmi_content = temp_vmi_info.read()
                if len(temp_vmi_content) == 0:
                    logger.debug('temp_vmi_info.txt is not exists')
                    continue
                else:
                    temp2vmi2info = eval(temp_vmi_content)
                    temp_vmi_info.close()

                if not temp2vmi2info.has_key(vmi2info['uuid']):
                    logger.info('temp_vmi_info.txt is not exists key: %s' % vmi2info['uuid'])
                    continue

                tmp2info = temp2vmi2info[vmi2info['uuid']]
                vmi2info['os_type'] = tmp2info['os_type']
                vmi2info['os_version'] = tmp2info['os_version']
                vmi2info['vmi_type'] = tmp2info['vmi_type']
                vmi2info['ref_temp'] = tmp2info['ref_temp']
                vmi2info['iso_path'] = tmp2info['iso_path']
                # 挂载模板使用的存储
                if tmp2info.has_key('temp_vstore_ip'):
                    self.__mount_store_dir(tmp2info['temp_vstore_ip'], tmp2info['temp_vstore_path'])

                vlan_cmd = "less %s/vm | grep %s | awk -F'=' '{print $2}'" % (self.tmp, vmi2info['uuid'])
                vlan = commands.getstatusoutput(vlan_cmd)[1].strip()
                logger.info('vlan_cmd: %s, vlan: %s' % (vlan_cmd, vlan))
                if len(vlan) > 0:
                    vmi2info['vlan'] = int(vlan) + 1

                disks = doc.getElementsByTagName('disk')
                for disk in disks:
                    mount_file = disk.getElementsByTagName('source')[0].getAttribute('file')
                    search_result = IP_CHECK.search(mount_file)
                    if search_result is None:
                        # 寻找portal的md5_address.json文件
                        vmc_md5 = mount_file.rsplit('/', 3)[1]
                        for address2md5 in vmc_md5_dicts:
                            md5s = address2md5.values()
                            if vmc_md5 in md5s:
                                original2portal2md5 = address2md5
                                break

                        if original2portal2md5 is not None:
                            for key, value in original2portal2md5.items():
                                if value == vmc_md5:
                                    vstore_ip = key
                                    break
                        else:
                            logger.error('original portal md5 is not exists')
                            continue
                    else:
                        vstore_ip = search_result.group()

                    # 挂载虚拟机磁盘存储
                    if vstore_ip is not None and vstore2path.has_key(vstore_ip):
                        vstore_path = vstore2path.get(vstore_ip, '/usr/local/hicloud-data/vstore')
                        self.__mount_store_dir(vstore_ip, vstore_path)

                    logger.info('mount_file value: %s' % mount_file)
                    if not os.path.exists(mount_file):
                        logger.info('%s is not exists' % mount_file)
                        # 删除不存在iso或则img文件的虚拟机配置文件
                        if os.path.exists(vmi_xml_file):
                            os.remove(vmi_xml_file)
                            continue

                    if disk.getAttribute('device') == 'cdrom':
                        vmi2info['iso_path'] = mount_file
                    elif disk.getAttribute('device') == 'disk':
                        vmi2info['disk_path'] = mount_file
                        try:
                            statistics_img_size_cmd = 'kvm-img info %s' % mount_file
                            logger.info('statistics_img_size_cmd value: %s' % statistics_img_size_cmd)
                            disk_size = commands.getstatusoutput(statistics_img_size_cmd)[1].split('\n')[2].split()[2][
                                        : -1]
                        except Exception as e:
                            logger.error('deploy img path is not exists!')
                            continue
                        logger.info('disk_size value: %s' % disk_size)
                        vmi2info['disk_size'] = disk_size
                        vmi2info['vstore_ip'] = vstore_ip
                        vmi2info['vstore_path'] = vstore2path.get(vstore_ip, '/usr/local/hicloud-data/vstore')

                logger.info('insert network info')
                vmi2info['interfaces'] = []
                interfaces = doc.getElementsByTagName('interface')
                vmi2info['nic_count'] = len(interfaces)
                for interface in interfaces:
                    interface2info = {}
                    interface2info['mac'] = interface.getElementsByTagName('mac')[0].getAttribute('address')
                    interface2info['tap'] = interface.getElementsByTagName('target')[0].getAttribute('dev')
                    if temp2vmi2info.has_key(vmi2info['uuid']):
                        interface2info['address'] = temp2vmi2info[vmi2info['uuid']]['interfaces'][interface2info['mac']]
                    vmi2info['interfaces'].append(interface2info)
                vmc2vmis['vmis'].append(vmi2info)

            backup_file_path = '%s/vmc/%s' % (self.dataRoot, vmc_address)
            if not os.path.exists(backup_file_path):
                os.system('touch %s' % backup_file_path)
            backup_file = open(backup_file_path, 'w')
            logger.info('vmc2vimx info: %s' % repr(vmc2vmis))
            backup_file.write(repr(vmc2vmis))
            backup_file.close()

            # 存在xml，不存在实例
            for vmi_xml_file in files:
                if vmi_xml_file.rsplit('/', 1)[1][: -4] not in domain_uuids:
                    # 重新定义虚拟机实例
                    try:
                        conn.defineXML(vmi_xml_file)
                    except:
                        # 删除不能进行实例化的虚拟机配置文件
                        os.remove(domain_xml)
            return 0
        except BaseException as e:
            logger.error('updateVMC is error: %s' % repr(e))
            return -1
        finally:
            conn.close()

    # 添加存储
    def addVstore(self, xml_desc):
        logger.info('***** addVstore is running *****')
        try:
            logger.info('add vstore xml: %s' % xml_desc)
            # 获取存储ip和存储路径
            vstore_ip, vstore_path = get_vstore_info(xml_desc)
            logger.info('vstore_ip value: %s, vstore_path value: %s' % (vstore_ip, vstore_path))
            if vstore_ip.strip() == '' or vstore_path.strip() == '':
                logger.error('Vstore path is not offered')
                return -1

            try:
                # 随机等待几秒钟，防止所有vmc同时执行mount操作，多并发有可能会导致nfs崩溃
                time.sleep(random.randint(1, 10))
                self.__mount_store_dir(vstore_ip, vstore_path)
            except Exception as e:
                logger.error('add vstore mount is error: %s' % repr(e))
                return -1

            logger.debug('hicloud-monitor')
            # 添加存储后执行汇报操作
            os.system('hicloud-monitor')
            return 0
        except Exception as err:
            logger.error('add vstore failed: %s' % repr(err))
            return -1

    # 修改NFS存储的IP地址
    def updateVstore(self, new_ip, old_ip, path):
        # 独立存储的IP修改的情况，Monitor无法向Portal汇报。暂不支持。
        logger.info('***** updateVstore is running *****')
        address2md5 = None  # get_address_md5() #add by cuilei
        if address2md5 is None or not address2md5.has_key(new_ip):
            logger.error('%s is not exists md5 info' % new_ip)
            return -1

        br0_address = get_vmc_address()
        local_ips = commands.getstatusoutput(
            "/sbin/ifconfig | grep 'inet addr' | grep -v '127.0.0.1' | awk '{print $2}' | awk -F':' '{print $2}'")[
            1].split('\n')
        logger.info('new_ip: %s, old_ip: %s, local_ips: %s' % (new_ip, old_ip, str(local_ips)))
        if new_ip in local_ips and new_ip != br0_address:
            # 下边的命令需要等待此命令执行结束
            commands.getstatusoutput('/sbin/ifconfig br0 %s' % new_ip)
            # 修改br0的ip地址
            os.system('/etc/init.d/run_openvswitch.sh')

        try:
            self.__mount_store_dir(new_ip, path, old_ip)
            conn = libvirt.open(None)
            if conn == None:
                logger.error('Failed to open connection to the hypervisor')
                return LibvirtOffErr

            try:
                # 修改虚拟机的配置文件
                vmi_xml_files = glob.glob('/etc/libvirt/qemu/*.xml')
                for xml_file in vmi_xml_files:
                    with open(xml_file, 'r') as f:
                        xml_content = f.read()

                    if xml_content.find(old_ip) != -1:
                        with open(xml_file, 'w') as f:
                            new_xml_content = xml_content.replace(old_ip, address2md5[new_ip])
                            f.write(new_xml_content)
                        conn.defineXML(xml_file)
            finally:
                conn.close()
            return 0
        except Exception as e:
            logger.error('updateVstore is error: %s' % repr(e))
            return -1

    # 删除存储
    def deleteVstore(self, xml_desc):
        logger.info('***** deleteVstore is running *****')
        try:
            logger.info('delete vstore xml: %s' % xml_desc)
            # 获取存储ip和存储路径
            vstore_ip, vstore_path = get_vstore_info(xml_desc)
            logger.info('vstore_ip value: %s, vstore_path value: %s' % (vstore_ip, vstore_path))
            if vstore_ip.strip() == '' or vstore_path.strip() == '':
                logger.error('Vstore path is not offered')
                return -1

            try:
                store_path = filter_address('%s/%s' % (self.nfsmountRoot, vstore_ip), vstore_ip)
                if os.path.ismount(store_path):
                    umount_cmd = 'umount -l %s' % store_path
                    logger.info('umount cmd: %s' % umount_cmd)
                    umount_result = commands.getstatusoutput(umount_cmd)
                    logger.info('umount result: %s' % repr(umount_result))
                    if umount_result[0] != 0:
                        logger.error('umount failed, error: %s' % umount_result[1])
                        return -1
                    else:
                        return 0
                elif os.path.islink(store_path):
                    destroy_link_result = commands.getstatusoutput('rm -rf %s' % store_path)
                    logger.info('rm link result: %s' % repr(destroy_link_result))
                    return 0
                else:
                    return 0
            except Exception as e:
                logger.error('umount vstore is error: %s' % repr(e))
                return -1
        except Exception as err:
            logger.error('add vstore failed: %s' % repr(err))
            return -1

    # 初始化当前虚拟机所用主机的存储挂载
    def init_mount_store(self, args):
        logger.info('***** init_mount_store is running *****')
        try:
            if type(args) == str:
                args = eval(args)

            logger.info('args value: %s' % repr(args))

            vstore_ip = args.vstore_ip.strip()
            vstore_path = args.vstore_path.strip()
            logger.info('vstore_ip: %s, vstore_path: %s' % (vstore_ip, vstore_path))

            if len(vstore_ip) == 0 or len(vstore_path) == 0:
                return -1

            self.__mount_store_dir(vstore_ip, vstore_path)
            logger.debug('init_mount_store() finished....')
        except BaseException as e:
            logger.error('init mount store is error: %s' % repr(e))
            return -1

    # function: Dnat configuration
    def confDnat(self, uuid, dnet_params=[]):
        boot = []
        shutdown = []
        for dnets in dnet_params:
            for vport in dnets['internal_ports']:
                pport = dnets['external_ports'][dnets['internal_ports'].index(vport)]
                start_cmd = 'iptables -t nat -A PREROUTING -p %s -d %s --dport %d -j DNAT --to %s:%d' % (
                    dnets['protocol'], dnets['external_ip'], pport, dnets['internal_ip'], vport)
                stop_cmd = 'iptables -t nat -D PREROUTING -p %s -d %s --dport %d -j DNAT --to %s:%d' % (
                    dnets['protocol'], dnets['external_ip'], pport, dnets['internal_ip'], vport)
                boot.append(start_cmd)
                shutdown.append(stop_cmd)
        boot.append('iptables -F')
        for iptables in boot:
            os.system(iptables)
        return 0

    def run(self, program, *args):
        pid = os.fork()
        if not pid:
            close_all()
            # os.close(0)
            # os.close(1)
            # os.close(2)
            # os.open('/dev/null', os.O_RDONLY)
            # os.open('/dev/null', os.O_WRONLY)
            # os.dup(1)
            os.execvp(program, (program,) + args)
        return pid

    def getTapname(self, vm_uuid):
	logger.info('***** getTapname *****')
        if not os.path.exists(self.tmp + VM):
            logger.error("Cannot find vm uuid map file!")
            return -1
        cf = ConfigParser.ConfigParser()
        VMI = VM+"/"+str(vm_uuid)
        cf.read(self.tmp + VMI)
        try:
            res = cf.get("tap", vm_uuid)
            return res
        except Exception as err:
            logger.error("No type entry for vswitch %s", vm_uuid)
            return -1	

    def getVlan(self, vm_uuid):
        logger.info('***** getVlan *****')
        if not os.path.exists(self.tmp + VM):
            logger.error("Cannot find vm uuid map file!")
            return -1
        cf = ConfigParser.ConfigParser()
	VMI = VM+"/"+str(vm_uuid)
        cf.read(self.tmp + VMI)
        try:
            res = cf.get("vlan", vm_uuid)
            return res
        except Exception as err:
            logger.error("No type entry for vswitch %s", vm_uuid)
            return -1

    # 为虚拟机添加内网地址
    def setVlan(self, vm_uuid, vlan_id,tap_name):
        logger.info('***** setVlan s running*****')
        cf = ConfigParser.ConfigParser()
	#/vmc160/hicloud/vmc/vlan
        if not os.path.exists(self.tmp + VM):
            mk_dir(self.tmp + VM)
	VMI = VM+"/"+str(vm_uuid)
        #/vmc160/hicloud/vmc/vlan/"uuid"
        if not os.path.exists(self.tmp + VMI):
            os.system("touch %s%s" % (self.tmp, VMI))
        time.sleep(random.randint(1, 5))
        cf.read(self.tmp + VMI)
        if "vlan" not in cf.sections():
            cf.add_section("vlan")
        cf.set("vlan", vm_uuid, vlan_id)
	if "tap" not in cf.sections():
	    cf.add_section("tap")
	cf.set("tap", vm_uuid, tap_name)
        cf.write(open(self.tmp + VMI, "w"))

    # 删除虚拟机内网地址
    def rmVlan(self, vm_uuid):
	if not os.path.exists(self.tmp + VM + "/" + str(vm_uuid)):
		logger.error("Not exists vlan file of vmi %s" % vm_uuid)
        cf = ConfigParser.ConfigParser()
        cf.read(self.tmp + VM + "/" + str(vm_uuid))
        cf.remove_option("vlan", vm_uuid)
        cf.write(open(self.tmp + VM + "/" + str(vm_uuid), "w"))

    def printDict(self, dicts):
	logger.info("printDict is running")
	try:
		for key, value in dicts.items():
			logger.debug("key: %s, value: %s"%(str(key),str(value)))
	except Exception as e:
		logger.error("printDict error:%s"%(str(e)))
		
    def infoVmi(self, uuid):
        logger.info("infoVmi is running")
        import libvirt
        dict_info = {'name':'', 'uuid':'', 'cpu_usage':0, 'status':-1, 'mem_total':0, 'disk_total':60}
        try:
                conn = libvirt.openReadOnly(None)
                dom = conn.lookupByUUIDString(uuid)
                #state, maxMemory, memory, num_vcpu, cpuTime
                vmiList = dom.info()
		maxMemory = vmiList[1]
		logger.info(maxMemory)
                time1 = vmiList[4]
                time.sleep(1)
                vmiList = dom.info()
		print "vmiList:"
		print vmiList
                time2 = vmiList[4]
		logger.info(time2-time1)
                cpu_usage = (time2-time1)/(pow(10,7))
		logger.info(cpu_usage)
                status = vmiList[0]
		maxMemory = vmiList[1]
		'''
                if status == 5:
                        status = 0
                elif status == 3:
                        status = 2
                elif status == 1:
                        status = 1
                else:
                        status = -1
		'''
                name = dom.name()
                dict_info = {'name':str(name), 'uuid':str(uuid), 'cpu_usage':int(cpu_usage), 'status':status, 'mem_total':int(maxMemory/1024/1024), 'disk_total':60}
		logger.info("result:")
		self.printDict(dict_info)
                return str(dict_info)
        except Exception as e:
                logger.error("infoVmi error:%s"%(str(e)))
                return str(dict_info)

    def infoVmc(self):
        logger.info("infoVmc is running")
        import psutil
        import time
        dict_info = {'cpu_usage':0, 'mem_usage':0, 'disk_usage':0, 'mem_total':0, 'disk_total':0, 'phy_on_num':0, 'phy_off_num':0}
        try:
                statvfs = os.statvfs('/')
                total_disk_space = statvfs.f_frsize * statvfs.f_blocks
                free_disk_space = statvfs.f_frsize * statvfs.f_bfree
                mem = psutil.virtual_memory()
                cpu_usage_list = psutil.cpu_percent(percpu=True)
		cpu_usage = 0
		for item in cpu_usage_list:
			cpu_usage = cpu_usage + item
		cpu_usage = cpu_usage/(len(cpu_usage_list))
                mem_usage = mem.used
                disk_usage = total_disk_space - free_disk_space
                mem_total = mem.total
                disk_total = total_disk_space
                phy_on_num = 1
                phy_off_num = 0
                dict_info['cpu_usage'] = int(cpu_usage)
                dict_info['mem_usage'] = int(mem_usage/(1024*1024*1024))
                dict_info['disk_usage'] = int(disk_usage/(1024*1024*1024))
                dict_info['mem_total'] = int(mem_total/(1024*1024*1024))
                dict_info['disk_total'] = int(disk_total/(1024*1024*1024))
                dict_info['phy_on_num'] = int(phy_on_num)
                dict_info['phy_off_num'] = int(phy_off_num)
		logger.info("result:")
                self.printDict(dict_info)
                return str(dict_info)

        except Exception as e:
                logger.error("error in infoVmc: %s"%(str(e)))
                return str(dict_info)

    def create_firewall(self, fwl_id, fwl_uuid, uuid, tag, mac1, mac2):
	logger.info("create_firewall is running")
	try:
		svmList = self.infoSVM(str(uuid))
		logger.debug("svmList:")
		logger.debug(svmList)
		tap_name = str(svmList[3])
		logger.debug('debug1')
		cmds = ['echo 123456|sudo -S virsh destroy %s'%(str(uuid)),'echo 123456 | sudo -S ifconfig %s down'%(tap_name), 'echo 123456 | sudo -S ovs-vsctl del-port br0 %s'%(tap_name)]
		logger.debug('debug2')
		for cmd in cmds:
			ret = self.openvswitch.exeCmd(cmd)
		br_name = 'bridge'+str(fwl_id) 
		logger.debug('debug3')     				
		tap_bridge = 'tapbridge'+str(fwl_id)	
		tap_firewall = 'tapfirewall'+str(fwl_id)  
		tap_list = [tap_bridge, tap_firewall]
		mac_list = [str(mac1), str(mac2)]
		if self.__create_firewall_xml(str(fwl_uuid), str(uuid), tap_list, mac_list)!=0:
			return 1
		cmds = ['echo 123456 | sudo -S ovs-vsctl add-br %s'%(br_name), 'echo 123456|sudo -S openvpn --mktun --dev %s'%(tap_bridge), 'echo 123456|sudo -S openvpn --mktun --dev %s'%(tap_firewall), 'echo 123456|sudo -S ovs-vsctl add-port br0 %s tag=%s'%(tap_bridge,tag), 'echo 123456|sudo -S ovs-vsctl add-port %s %s tag=%s'%(br_name, tap_firewall,tag), 'echo 123456|sudo -S ifconfig %s up'%(tap_bridge), 'echo 123456|sudo -S ifconfig %s up'%(tap_firewall), 'echo 123456|sudo -S ovs-vsctl add-port %s %s tag=%s'%(br_name, tap_name, tag), 'echo 123456|sudo -S ifconfig %s up'%(tap_name), 'echo 123456 | sudo -S virsh start %s'%(str(uuid)), 'echo 123456|sudo -S virsh define %s'%('/vmc160/firewall_'+str(uuid)+'.xml'), 'echo 123456|sudo -S virsh start %s'%('firewall_'+str(uuid))]
		for cmd in cmds:
                        ret = self.openvswitch.exeCmd(cmd)
		return 0
	except Exception as e:
		logger.error("create_firewall error:%s"%(str(err)))
		return 1	

    def del_firewall(self, fwl_id, uuid):
	logger.info("del_firewall is running")
	try:
		svmList = self.infoSVM(str(uuid))
		br_name = 'bridge'+str(fwl_id)  
                tap_name = str(svmList[3])
		tap_bridge = 'tapbridge'+str(fwl_id)    
                tap_firewall = 'tapfirewall'+str(fwl_id)  
		cmds = ['echo 123456|sudo -S ifconfig %s down'%(tap_name),'echo 123456|sudo -S ifconfig %s down'%(tap_bridge), 'echo 123456|sudo -S ifconfig %s down'%(tap_firewall),'echo 123456|sudo -S ovs-vsctl del-port br0 %s'%(tap_bridge), 'echo 123456|sudo -S ovs-vsctl del-port %s %s'%(br_name, tap_firewall), 'echo 123456|sudo -S ovs-vsctl del-port %s %s'%(br_name, tap_name), 'echo 123456 | sudo -S ovs-vsctl del-br %s'%(br_name), 'echo 123456|sudo -S virsh destroy %s'%('firewall_'+str(uuid)), 'echo 123456|sudo -S virsh undefine %s'%('firewall_'+str(uuid)), 'rm -rf /vmc160/firewall_%s.img'%(str(uuid)), 'rm -rf /vmc160/firewall_%s.xml'%(str(uuid)), 'echo 123456|sudo -S openvpn --rmtun --dev %s'%(tap_bridge), 'echo 123456|sudo -S openvpn --rmtun --dev %s'%(tap_firewall), 'echo 123456 | sudo -S virsh destroy %s'%(str(uuid)), 'echo 123456 | sudo -S ovs-vsctl add-port br0 %s tag=0'%(tap_name), 'echo 123456|sudo -S ifconfig %s up'%(str(uuid)),'echo 123456 | sudo -S virsh start %s'%(str(uuid))]
		for cmd in cmds:
                        ret = self.openvswitch.exeCmd(cmd)
		return 0
	except Exception as e:
		logger.error("del_firewall error:%s"%(str(e)))
		return 1

    def vmc_strerror(self, errno):
        if errno == SaveFileErr:
            return "Failed to create configure file"

        if errno == DownLoadCertErr:
            return "Failed to download CA cert, client cert and client key"

        if errno == VSWConfNotExistErr:
            return "VSwitch configure file not exists"

        if errno == LibvirtOffErr:
            return "Failed to open connection to the hypervisor"

        if errno == VPNConfNotExistErr:
            return "VPN configure file not exists"

        if errno == CreateNetXMLErr:
            return "Failed to create network xml file"

        if errno == IfconfigUPErr:
            return "Failed to ifconfig up"

        if errno == VSwitchOffErr:
            return "Network don't exist"

        if errno == IfconfigDownErr:
            return "Failed to ifconfig down"

        if errno == OtherException:
            return "Other Exception throw"

        if errno == DestroyVSwitchErr:
            return "Failed to destroy vswitch"

        if errno == ParseConfErr:
            return "Failed to parse configure file"

        if errno == StartVSwitchErr:
            return "Failed to start vswitch"

        if errno == CreateVMErr:
            return "Failed to create vm"

        if errno == ShutdownVMErr:
            return "Failed to shutdown vm"

        if errno == UUIDNullErr:
            return "UUID is Null"

        if errno == DownloadRFSErr:
            return "Failed to download root file system"

        if errno == CreateVMImgErr:
            return "Failed to create vm image"

        if errno == VMImgNotExistErr:
            return "VM image not exist"

        if errno == RemoveVMDirErr:
            return "Failed to remove vm directory"

        if errno == VMCErr:
            return "VMC Error"

'''
if __name__ == "__main__":
    	print "this is a debug test"
	uuid = '107b03a6-5d99-11e6-9477-000c29bf8d39'
	xml = '<vNode><Uuid>107b03a6-5d99-11e6-9477-000c29bf8d39</Uuid><Type> </Type><Hostname>0810-test1</Hostname><Desc> </Desc><CpuCnt>1</CpuCnt><Mem>256</Mem><NicCnt>1</NicCnt><DiskSize>1</DiskSize><VstoreIp>127.0.0.1</VstoreIp><VstorePath>/var/lib/ivic/vstore</VstorePath><StorageType>local</StorageType><OsType>Windows</OsType><OsVersion>7</OsVersion><vTemplateRef> </vTemplateRef><IsoPath>/var/lib/ivic/vmc/nfsmount/192.168.50.129/iso/windows7.iso</IsoPath><NIC id=\'1\'><Vlan>2</Vlan><Address>192.168.60.101</Address><Netmask>255.255.255.0</Netmask><Gateway>192.168.60.1</Gateway><MAC>31:19:83:58:12:31</MAC><DNS>1.2.4.8</DNS></NIC><Password> </Password></vNode>'

	logger.info('hello world')
'''
def tryMain():
      server = ServerClass()
      print server.infoVmc()      

#tryMain()














