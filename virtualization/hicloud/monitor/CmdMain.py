#!/usr/bin/env python
# -*- coding: utf-8 -*-
import signal

'''
The monitor is an agent installed in VMC host, its responsibility includes:
 1) Collect information from VMC host and its hosted virtual machines
 2) Send the collected information to the iVCS portal by RESTful interface using curl tool
'''

import os
import commands
import libvirt
import sys, libxml2, time, subprocess, re
from hicloud.core import Config, project_path, Logging
from hicloud.core.Utils import check_pid_file

# read entries from configuration files
config_monitor_path = project_path("/etc/hicloud/monitor.yaml")
config_daemon_path = project_path("/etc/hicloud/daemon.yaml")
config = Config.load(config_monitor_path)
pid_file = project_path("%s/monitor.pid" % config['run_dir'])
log_file = project_path("%s/monitor.log" % config['log_dir'])

# add by cuilei, May 2016
config_vstore_path = project_path("/etc/hicloud/vstore.yaml")
config_vstore = Config.load(config_vstore_path)

# log handler
logger = Logging.get_logger(__name__, filename=log_file, default=True)

NORESULT = "0"


def exe_timeout_command(command, timeout):
    ''' 执行OS命令时限定超时时间，单位为秒 ；超时时，返回None '''
    try:
        import subprocess, datetime, os, signal, time
        p = subprocess.Popen(command, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp)
        t0 = datetime.datetime.now()
        while p.poll() is None:
            if (datetime.datetime.now() - t0).seconds < timeout:
                continue
            else:
                os.kill(-p.pid, signal.SIGKILL)
                os.waitpid(-1, os.WNOHANG)
                return None
        return p.stdout.readlines()
    except Exception as e:
        logger.error("Error in exe_timeout_command(%s): %s" % (command, e.message))
        return None


def exe_command(command):
    try:
        pipe = os.popen(command, "r")
        result = pipe.readlines()
        return result
    except Exception as err:
        return None
    finally:
        pipe.close()


# 获取主机cpu信息
def get_pm_cpu_info():
    logger.info('***** get_pm_cpu_info is running *****')
    cpu_type = ''
    cpu_num = 0
    cpu_usage = ''
    cpu_info = []
    try:
        cputype_line = exe_command("cat /proc/cpuinfo | grep -m 1 'model name'")
        cpu_type = cputype_line[0].split(":")[1][1:].strip()
        cpunum_lines = exe_command("cat /proc/cpuinfo | grep 'processor'")
        cpu_num = int(cpunum_lines[len(cpunum_lines) - 1].split()[2]) + 1
        cputime_line = exe_command("head -n 1 /proc/stat")[0]

        cputime_slice = cputime_line.split()
        logger.info("cputime_slice: %s" % cputime_slice)

        t1 = int(cputime_slice[1])
        t2 = int(cputime_slice[2])
        t3 = int(cputime_slice[3])
        t4 = int(cputime_slice[4])
        t_all_1 = 0
        for slice in cputime_slice[1:]:
            t_all_1 = t_all_1 + int(slice)

        time.sleep(1)
        cputime_line = exe_command("head -n 1 /proc/stat")[0]
        cputime_slice = cputime_line.split()
        t1 = int(cputime_slice[1]) - t1
        t2 = int(cputime_slice[2]) - t2
        t3 = int(cputime_slice[3]) - t3
        t4 = int(cputime_slice[4]) - t4
        t_all_2 = 0
        for slice in cputime_slice[1:]:
            t_all_2 = t_all_2 + int(slice)

        cpu_usage = float(t1 + t2 + t3) / (t_all_2 - t_all_1)
        cpu_info.append(cpu_type)
        cpu_info.append(str(cpu_num))
        cpu_info.append(str(cpu_usage))
        return cpu_info
    except Exception as e:
        logger.error("Error in get_cpu_info(), error: %s" % e.message)
        return [NORESULT, NORESULT, NORESULT]


# 获取第一个网桥设备号
def get_pm_default_interface():
    logger.info('***** get_pm_default_interface is running *****')
    try:
        routes = exe_command("/sbin/route -n | sed '1,2d' | grep 'UG'")
        return routes[0].split()[7]
    except Exception as e:
        logger.error("Error in get_default_interface, error: %s" % e.message)
        return "eth0"


# 获取主机磁盘信息
def get_pm_disk_info():
    logger.info('***** get_pm_disk_info is running *****')
    disk_device = ''
    disk_total = ''
    disk_free = ''
    disk_info = []
    try:
        disklines = exe_timeout_command("df -P | grep '^\/dev\/'", 10)
        if not disklines:
            return [NORESULT, NORESULT, NORESULT]

        for line in disklines:
            disk_device += line.split()[0] + " "
            disk_total += line.split()[1] + " "
            disk_free += line.split()[3] + " "
        disk_info.append(disk_device)
        disk_info.append(disk_total)
        disk_info.append(disk_free)
        return disk_info
    except Exception as e:
        logger.error("Error in get_disk_info(), error: %s" % e.message)
        return [NORESULT, NORESULT, NORESULT]


# 获取指定网桥下主机的ip地址，一般情况下ifname值为br0
def get_pm_ip(ifname="eth0"):
    logger.info('***** get_pm_ip is running *****')
    try:
        ip_line = exe_command("/sbin/ifconfig " + ifname + " | grep 'inet addr:'")
        return [ip_line[0].split(":")[1].split()[0]]
    except Exception as e:
        logger.error("Error in get_ip(), error: %s" % e.message)
        return ["127.0.0.1"]


def get_pm_hostname():
    logger.info('***** get_pm_hostname is running *****')
    try:
        line = exe_timeout_command("hostname -f", 10)
        return line[0].strip()
    except Exception as e:
        logger.error("Error in get_pm_hostname(), error: %s" % e.message)
        return [NORESULT]


def get_license_HID():
    logger.info('***** get_license_HID is running *****')
    return "1"
    try:
        with open('/etc/hicloud/license') as f:
            for line in f.readlines():
                if line.startswith('HardwareID'):
                    return line.split()[1]
    except:
        logger.error("Error in get_license_HID(), error: %s" % e.message)
    return [NORESULT]


# 获取主机内存信息
def get_pm_mem_info():
    logger.info('***** get_pm_mem_info is running *****')
    mem_info = []
    try:
        meminfo_lines = exe_command("cat /proc/meminfo")
        mem_info.append(str(int(meminfo_lines[0].split()[1])))
        mem_info.append(
            str(int(meminfo_lines[1].split()[1]) + int(meminfo_lines[2].split()[1]) + int(meminfo_lines[3].split()[1])))
        return mem_info
    except Exception as e:
        logger.error("Error in get_mem_info(), error: %s" % e.message)
        return [NORESULT, NORESULT]


# 获取主机的网卡信息
def get_pm_network_info():
    logger.info('***** get_pm_network_info is running *****')
    # net_info = [net_ifname,net_tx,net_rx]
    network_info = []
    net_ifname = ""
    net_tx = ""
    net_rx = ""
    try:
        eth_list = exe_command("/sbin/ifconfig | grep ^eth")
        for eth in eth_list:
            cur_eth_name = eth.split()[0]
            net_ifname += cur_eth_name + " "
            command = "/sbin/ifconfig " + cur_eth_name + "| grep 'TX bytes:'"
            tx_line = exe_command(command)[0]
            net_tx += tx_line.split("(")[2].split()[0] + " "
            net_rx += tx_line.split("(")[1].split()[0] + " "
        network_info.append(net_ifname)
        network_info.append(net_tx)
        network_info.append(net_rx)
        return network_info
    except Exception as e:
        logger.error("Error in get_network_info(), error: %s" % e.message)
        return [NORESULT, NORESULT, NORESULT]


# 获取主机网卡数量
def get_nic_num():
    logger.info('***** get_nic_num is running *****')
    cmd = 'lspci | grep Ethernet | wc -l'
    try:
        ret = exe_command(cmd)
        return str(ret[0]).strip()
    except Exception as err:
        return '0'


# 获取主机距离上次关机运行时间
def get_pm_running_time():
    logger.info('***** get_pm_running_time is running *****')
    cmd = 'uptime'
    # two kinds of result
    # 17:28:51 up 12 days,    2:52,    6 users,
    # 15:20:08 up 21 days, 43 min, 9 users,
    # 17:28:36 up    4:45,    5 users,
    try:
        ret = exe_command(cmd)[0].strip()
        has_day = ret.find('day')
        has_min = ret.find('min')
        ret_list = ret.split()
        if has_day == -1:  # no days, just hours
            if has_min == -1:
                hours = ret_list[2].split(':')[0]
            else:
                hours = 0
            return str(hours)
        else:  # days
            days = int(ret_list[2])
            if has_min == -1:  # no minutes
                hours = int(ret_list[4].split(':')[0])
            else:
                hours = 0  # minutes
            hours = days * 24 + hours
            return str(hours)
    except Exception as err:
        return '0'


# 获取虚拟机分区信息
def get_domain_device_path_from_xml(vm_xml_doc, device_name):
    logger.info('***** get_domain_device_path_from_xml is running *****')
    doc = libxml2.readDoc(vm_xml_doc, None, None, libxml2.XML_PARSE_NOENT)
    ctxt = doc.xpathNewContext()
    res = ctxt.xpathEval("/domain/devices/%s/target[@dev]" % device_name)
    if type(res) != type([]) or len(res) == 0:
        doc.free()
        return None
    disk_paths = []
    for i in xrange(len(res)):
        disk_paths.append(res[i].properties.content)
    doc.free()
    return disk_paths


# 获取虚拟机磁盘使用信息
def get_domain_disk_info(conn, domain):
    logger.info('***** get_domain_disk_info is running *****')
    try:
        # 获取<target dev='hdc' bus='ide'/>
        disk_paths = get_domain_device_path_from_xml(domain.XMLDesc(0), "disk")
        disk_read = 0
        disk_write = 0
        if disk_paths == None:
            return [NORESULT, NORESULT, NORESULT]
        for disk_path in disk_paths:
            disk_read += float(domain.blockStats(disk_path)[1])
            disk_write += float(domain.blockStats(disk_path)[3])
        return [":".join(disk_paths), str(disk_read), str(disk_write)]
    except BaseException as e:
        logger.error('read vmi disk is error: %s' % repr(e))
        return [NORESULT, NORESULT, NORESULT]


# 获取虚拟机网络接口信息
def get_domain_vif_info(conn, domain):
    logger.info('***** get_domain_vif_info is running *****')
    try:
        # 获取 <target dev='tap7ed5fab88900'/>
        vif_paths = get_domain_device_path_from_xml(domain.XMLDesc(0), "interface")
        vif_tx = 0
        vif_rx = 0
        if vif_paths == None:
            return [NORESULT, NORESULT, NORESULT]
        for vif_path in vif_paths:
            vif_tx += float(domain.interfaceStats(vif_path)[0])
            vif_rx += float(domain.interfaceStats(vif_path)[4])
        return [":".join(vif_paths), str(vif_tx), str(vif_rx)]
    except BaseException as e:
        logger.error('read vif info is error: %s' % repr(e))
        return [NORESULT, NORESULT, NORESULT]


# 获取虚拟机端口号
def get_domain_vnc_port(domain_id, uuid):
    logger.info('***** get_domain_vnc_port is running *****')
    try:
        vncdisplay = exe_command("virsh vncdisplay %s" % domain_id)
        return vncdisplay[0].split(":")[1].strip()
    except Exception as e:
        logger.error("Error in get vnc port of domain %s, error: %s" % (domain_id, e.message))
        return NORESULT


# 获取虚拟机信息
def get_domains_info(conn, hypervisor_type, domain_names):
    logger.info('***** get_domains_info is running *****')
    domains_info = []
    status = {1: 'running', 2: 'unknown', 3: 'paused', 5: 'stopped'}

    try:
        for name in domain_names:
            domain_info = []
            try:
                domain = conn.lookupByName(name)
            except Exception as e:
                logger.info("Domain %s is not found" % name)
                continue

            # 虚拟机uuid
            domain_info.append(domain.UUIDString())  # vm_uuid
            # 虚拟机name(对应虚机hostname字段)
            domain_info.append(domain.name())  # vm_name
            # 虚机运行信息
            vm_infos = domain.info()
            # 虚拟机执行状态
            vmi_status = status[vm_infos[0]]
            logger.info('vmi name: %s, status: %s' % (name, vmi_status))
            if vmi_status == 'paused': continue  # Fix BUG: 打快照的时间很长的时候，暂停的状态就会汇报到前台的情况。
            domain_info.append(vmi_status)  # vm_state
            # 虚拟机内存总大小
            domain_info.append(vm_infos[1])  # vm_memtotal
            # 虚拟机内存剩余大小
            domain_info.append(vm_infos[1] - vm_infos[2])  # vm_memfree
            # 虚拟机开机时间（单位：秒）
            domain_info.append(float(vm_infos[4]) / 1000000000)  # vm_cputime(seconds)
            # 虚拟机vnc端口只有在开机状态下才汇报
            if vmi_status in ('running', 'paused'):
                domain_info.extend(get_domain_disk_info(conn, domain))
                domain_info.extend(get_domain_vif_info(conn, domain))
                domain_info.append(get_domain_vnc_port(domain.ID(), domain.UUIDString()))
            else:
                domain_info.extend([NORESULT, NORESULT, NORESULT])
                domain_info.extend([NORESULT, NORESULT, NORESULT])
                domain_info.append('-1')
            domains_info.append(domain_info)
        return domains_info
    except Exception as e:
        logger.error('monitor vmi is error: %s' % e.message)
        return ''


# 将虚拟机监控信息保存到文件
def save_domains_to_file(domain_info, domain_file):
    logger.info('***** save_domains_to_file is running *****')
    if os.path.exists(domain_file):
        os.remove(domain_file)

    try:
        f = open(domain_file, 'w')
        f.write(repr(domain_info))
    except Exception as err:
        logger.error("Save domain info to file error: %s" % err.message)
    finally:
        f.close()


# 从文件中获取虚拟机监控信息
def get_domains_from_file(domain_file):  # get last monitor information from lcoal file
    logger.info('***** get_domains_from_file is running *****')
    if not os.path.exists(domain_file):
        return []
    try:
        f = open(domain_file, 'r')
        content = f.readline()
        con_list = eval(content)  # list
        return con_list
    except Exception as err:
        logger.error("Get domain info from file % error: %s" % (domain_info, err.message))
        return []
    finally:
        f.close()


class VMInstance(object):
    def __init__(self):
        self.vm_uuid = ""
        self.vm_name = ""
        self.vm_state = ""
        self.vmem_total = ""
        self.vmem_free = ""
        self.vcpu_usage = ""
        self.vdisk_names = ""
        self.vdisk_read = ""
        self.vdisk_write = ""
        self.vif_names = ""
        self.vif_tx = ""
        self.vif_rx = ""
        self.vnc_port = ""

    def load_from_list(self, list_items):
        self.vm_uuid = list_items[0]
        self.vm_name = list_items[1]
        self.vm_state = list_items[2]
        self.vmem_total = str(int(list_items[3]) / 1024.0)
        self.vmem_free = str(int(list_items[4]) / 1024.0)
        self.vcpu_usage = list_items[5]
        self.vdisk_names = list_items[6]
        self.vdisk_read = list_items[7]
        self.vdisk_write = list_items[8]
        self.vif_names = list_items[9]
        self.vif_tx = list_items[10]
        self.vif_rx = list_items[11]
        self.vnc_port = list_items[12]

    def parse_to_string(self):
        str_format = "%s"
        ret = []
        ret.append(str_format % (self.vm_uuid))
        ret.append(str_format % (self.vm_name))
        ret.append(str_format % (self.vm_state))
        ret.append(str_format % (self.vmem_total))
        ret.append(str_format % (self.vmem_free))
        ret.append(str_format % (self.vcpu_usage))
        ret.append(str_format % (self.vdisk_names))
        ret.append(str_format % (self.vdisk_read))
        ret.append(str_format % (self.vdisk_write))
        ret.append(str_format % (self.vif_names))
        ret.append(str_format % (self.vif_tx))
        ret.append(str_format % (self.vif_rx))
        ret.append(str_format % (self.vnc_port))
        return ret

    def update_info(self, instance):
        self.vmem_free = instance.vmem_free
        self.vcpu_usage = instance.vcpu_usage

    def update_stopped_info(self):
        self.vm_state = "stopped"
        self.vmem_free = self.vmem_total
        self.vcpu_usage = 0.0
        self.vdisk_read = 0.0
        self.vif_tx = NORESULT
        self.vif_rx = NORESULT
        self.vnc_port = -1

    def __repr__(self):
        ret = self.parse_to_string()
        return ret


# 将虚拟机信息解析为实例对象
def parse_vminstances(domain_info):
    logger.info('***** parse_vminstances is running *****')
    vm_instances = []
    uuids = []
    for last_item in domain_info:
        vm_instance = VMInstance()
        vm_instance.load_from_list(last_item)
        vm_instances.append(vm_instance)
        uuids.append(vm_instance.vm_uuid)
    return vm_instances, uuids


# 将已停止的虚拟机信息加入到监控列表中
def compare_last_new(last_qemu_domains_info, new_qemu_domains_info):
    logger.info('***** compare_last_new is running *****')
    ret_info = []
    # get last monitor information
    last_vm_instances, last_uuids = parse_vminstances(last_qemu_domains_info)
    new_vm_instances, new_uuids = parse_vminstances(new_qemu_domains_info)

    # 将监控不到的虚拟机设置为停止状态，并添加到监控信息中
    for last_instance in last_vm_instances:
        if last_instance.vm_uuid not in new_uuids:  # vm_instance is stoped
            last_instance.update_stopped_info()
            new_vm_instances.append(last_instance)

    # 格式化虚拟机汇报信息
    ret = []
    for vmi in new_vm_instances:
        ret.append(vmi.parse_to_string())
    return ret


def do_libvirt_monitor():
    logger.info('***** do_libvirt_monitor is running *****')
    libvirt_items = commands.getstatusoutput('/etc/init.d/libvirt-bin status')
    logger.info('monitor libvirt result: %s' % repr(libvirt_items))
    virsh_items = commands.getstatusoutput('virsh list')
    logger.info('virsh list result: %s' % repr(virsh_items))
    if 'failed' in libvirt_items[1] or 'Connection reset by peer' in virsh_items[1] or 'Connection refused' in \
            virsh_items[1]:
        os.system('/etc/init.d/libvirt-bin restart')


def do_vmc_monitor(argv):
    logger.info('***** do_vmc_monitor is running *****')
    argv = argv[1:]
    client_key = "/root/123.pem"
    server_cert = "/root/ca.crt"
    send_url = "/vmcs/api"
    capability = ''  # default capability = empty string
    port = '8080'
    arg_names = ["address", "status", "cpu_type", "cpu_num", "cpu_usage",
                 "mem_total", "mem_free", "disk_device", "disk_total", "disk_free",
                 "net_ifname", "net_tx", "net_rx", "capability", "port", "nics_num", "running_time",
                 "vm_uuid", "vm_name", "vm_state", "vmem_total", "vmem_free",
                 "vcpu_usage", "vdisk_names", "vdisk_read", "vdisk_write", "vif_names",
                 "vif_tx", "vif_rx", "vnc_port"]  # nics_num added by cuilei
    # In fact, "vcpu_usage" corresponds to the column 'runtime1' in portal db vmis table.
    # vdisk_name, vif_name are used for show the collectd info in portal.
    arg_values = []

    # analyse the file monitor.yaml
    try:
        config_monitor = Config.load(config_monitor_path)
        client_key = config_monitor['client_key']
        server_cert = config_monitor['server_cert']
        send_url = config_monitor['monitor_send_url']
        # config item 'capability' is list, convert it to a space separated string
        capability = ' '.join(config_monitor['capabilities'])
    except Exception as e:
        logger.error("Could not find config in %s, use default setting, error: %s" % (config_monitor_path, e.message))

    # analyse the file daemon.yaml to get 'port'
    try:
        port = Config.load(config_daemon_path)['listen_port']
    except Exception as e:
        logger.error("Could not find config in %s, use default setting, error: %s" % (config_daemon_path, e.message))

    # collect pm statistics from each function
    arg_values += get_pm_ip(get_pm_default_interface())
    arg_values += ["online"]
    arg_values += get_pm_cpu_info()
    arg_values += get_pm_mem_info()
    arg_values += get_pm_disk_info()
    arg_values += get_pm_network_info()
    arg_values += [capability]
    arg_values += [str(port)]
    arg_values += [get_nic_num()]
    arg_values += [get_pm_running_time()]
    # arg_values += [get_license_HID()] # comment this, add by cuilei, May 2016
    logger.info("Arg values are " + str(arg_values))
    # create conn to xen and kvm hypervisor
    xen_support = False
    qemu_support = False
    xen_domains_ID = []
    qemu_domains_ID = []
    conn_xen = None
    conn_qemu = None
    qemu_domains_info = []

    # 监控libvirt的运行状态
    do_libvirt_monitor()

    try:
        # conn_qemu = libvirt.openReadOnly("qemu:///system")
        conn_qemu = libvirt.open(None)
    except Exception as e:
        logger.error("libvirt is failed")

    if conn_qemu != None:
        qemu_support = True
        if conn_qemu.numOfDomains() > 0:
            # 获取当前主机所有虚拟机的名称列表
            domain_names = [item.split()[1] for item in commands.getstatusoutput('virsh list --all')[1].split('\n')[2:]
                            if len(item) > 0]
            logger.info('domain_names: %s' % domain_names)
            # 获取在运行虚拟机id列表
        #            qemu_domains_ID = conn_qemu.listDomainsID()
        else:
            logger.info("No qemu domain!")

    new_vm_instances_start = []
    new_vm_instances_end = []
    # collect domain statistics
    if qemu_support == True and conn_qemu.numOfDomains() > 0:
        qemu_domains_info_start = get_domains_info(conn_qemu, "qemu", domain_names)
        new_vm_instances_start, new_uuids_start = parse_vminstances(qemu_domains_info_start)

        time.sleep(1)

        qemu_domains_info_end = get_domains_info(conn_qemu, "qemu", domain_names)
        new_vm_instances_end, new_uuids_end = parse_vminstances(qemu_domains_info_end)

        if len(new_vm_instances_start) != len(new_vm_instances_end):
            return

        for instance_id in range(len(new_vm_instances_start)):
            new_vm_instances_end[instance_id].vcpu_usage = (new_vm_instances_end[instance_id].vcpu_usage -
                                                            new_vm_instances_start[instance_id].vcpu_usage) / 5.0 / 100

    conn_qemu.close()

    # 格式化虚拟机汇报信息
    new_qemu_domains_info = []
    for vmi in new_vm_instances_end:
        new_qemu_domains_info.append(vmi.parse_to_string())

    # 将每一个虚拟机信息使用空格分隔
    for i in xrange(13):  # 13= len(arg_names)-15
        value = ""
        if new_qemu_domains_info != []:
            for qemu_domain_item in new_qemu_domains_info:
                value += str(qemu_domain_item[i]) + " "
        arg_values += [value]

    # cmd = "curl -X PUT --cert %s --cacert %s -d \"" % (client_key, server_cert)
    cmd = "curl -X POST -d \""  # add by cuilei, May 2016
    logger.info("arg_values: %s, arg_names: %s" % (len(arg_values), len(arg_names)))

    for i in xrange(len(arg_names)):
        # cmd += "VirtualMachineContainer[%s]=%s&" % (arg_names[i], arg_values[i])
        cmd += "VMC[%s]=%s&" % (arg_names[i], arg_values[i])
    # add by cuilei, May, 2016
    cmd += "\" -H \"Accept: text/xml\" %s" % send_url
    logger.info("cmd: %s" % cmd)
    os.system(cmd)
    logger.info(cmd)


def ping_targets(targets, ping_count=5):
    logger.info('***** ping_targets is running *****')
    create_sub_process = lambda x: subprocess.Popen(['ping', '-w', '1', '-c', '%s' % ping_count, x],
                                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # 依次遍历ip列表
    processes = map(create_sub_process, targets)
    map(lambda x: x.wait(), processes)
    # 获取标准输出
    stdouts = map(lambda x: x.stdout.readlines(), processes)
    # 获取错误信息
    stderrs = map(lambda x: x.stderr.readlines(), processes)

    # 5 packets transmitted, 5 received, 0% packet loss, time 4001ms
    # 匹配无法连接的包丢失率
    prog_pkg_lost = re.compile(r".*, ([0-9\.]+%) packet loss,.*")
    match = lambda x: prog_pkg_lost.match(x)

    def get_pkg_lost(stdout):
        # 匹配无法连接的包丢失率
        m = map(match, stdout)
        # 过滤掉未匹配上的元素
        mm = filter(None, m)
        if mm is not None and len(mm) != 0:
            # 返回匹配出的包丢失率
            return mm[0].groups()[0]
        else:
            return ''

    # 返回所有没有ping通主机的包丢失率
    pkg_losts = map(lambda x: get_pkg_lost(x), stdouts)

    # rtt min/avg/max/mdev = 0.117/0.140/0.159/0.021 ms
    # 匹配正常连接的信息
    prog_rtt = re.compile(r"rtt min/avg/max/mdev = ([0-9\.]*)/([0-9\.]*)/([0-9\.]*)/([0-9\.]*) ms")
    match = lambda x: prog_rtt.match(x)

    def get_rtt(stdout):
        m = map(match, stdout)
        # 过滤掉未匹配上得元素
        mm = filter(None, m)
        if mm is not None and len(mm) != 0:
            return mm[0].groups()
        else:
            return ['', '', '', '']

    # 所有正常连接的ping信息
    rtts = map(lambda x: get_rtt(x), stdouts)
    return pkg_losts, rtts


def get_pm_disk_info_vstore(argv):
    logger.info('***** get_pm_disk_info_vstore is running *****')
    rtn = []
    # get the local store info
    config_vmc_path = project_path("/etc/hicloud/vmc.yaml")
    vmc_config = Config.load(config_vmc_path)
    mountpoint = vmc_config['nfsmount_root']
    tmp0 = exe_timeout_command("find %s -type l -exec ls -l {} \;" % mountpoint, 10)
    # 本机存储ip
    local_vstore_ip = commands.getstatusoutput(
        "/sbin/ifconfig | grep -A 1 'br0' | grep 'inet addr:' | grep -v '127.0.0.1' | awk '{print $2}' | awk -F':' '{print $2}'")[
        1]
    # 本地存储已经在用
    if tmp0 and tmp0[0].find('->') != -1:
        #        #使用链接获取本地存储使用情况
        #        ip = tmp0[0].split('->')[0].split('/')[-1]
        path = tmp0[0].split('->')[-1]
        local_vstore_info = exe_timeout_command("df -P %s" % path, 10)
        if local_vstore_info is not None and len(local_vstore_info) == 2:
            items = local_vstore_info[1].split()
            rtn.append((local_vstore_ip.strip(), path.strip(), str(int(items[1]) / 1024.0 / 1024.0),
                        str(int(items[2]) / 1024.0 / 1024.0)))
    else:
        # 本地存储还没有使用
        disk_total = 0
        disk_free = 0
        disklines = exe_timeout_command("df -P | grep '^\/dev\/'", 20)
        sub_vstore_path = commands.getstatusoutput("less /etc/exports | grep -v '^\#'")[1].split()[0][:5]
        for line in disklines:
            items = line.split()
            if sub_vstore_path in items[-1]:
                logger.info('sub_vstore_path: %s, disk partition path: %s' % (sub_vstore_path, items[-1]))
                disk_total = int(items[1]) / 1024.0 / 1024.0
                disk_free = int(items[3]) / 1024.0 / 1024.0
                break

        rtn.append((local_vstore_ip.strip(), '', str(disk_total), str(disk_total - disk_free)))

    # 汇报本地挂载的存储大小
    tmp0 = exe_timeout_command("df -P -t nfs", 10)
    # 第一行为标题，从第二行开始为挂载点数据
    if tmp0 and len(tmp0) >= 2:
        for i in range(len(tmp0)):
            if i == 0:
                continue
            tmp1 = tmp0[i].split()
            temp_items = tmp1[0].split(':')
            rtn.append((temp_items[0].strip(), temp_items[1].strip(), tmp1[1], tmp1[2]))

    return rtn


#    tmp_rtn = []
#    for one in rtn:
#        tmp_rtn.append( one.rfill(2))
#    return tmp_rtn

def do_vstore_monitor(argv):
    logger.info('***** do_vstore_monitor is running *****')
    argv = argv[1:]
    config_monitor = Config.load(config_monitor_path)
    client_key = config_monitor['client_key']
    server_cert = config_monitor['server_cert']
    send_url = config_monitor['vstore_send_url']

    arg_names = ["ip_address", "storage_path", "total_storage", "used_storage"]
    arg_values = get_pm_disk_info_vstore(argv)
    if not arg_values:
        return

    # send monitor data to portal
    # cmd = "curl -X PUT --cert " + client_key + " --cacert " + server_cert + " -d \"count=" + str(len(arg_values)) + "&"
    # add by cuilei, May 2016
    cmd = "curl -X POST " + " -d \"count=" + str(len(arg_values)) + "&"

    # for i in xrange(len(arg_values)):
    #    for j in xrange(len(arg_names)):
    #        cmd += "storage" + str(i) + "[" + arg_names[j] + "]=" + arg_values[i][j] + "&"

    # add by cuilei
    for i in range(len(arg_names)):
        one_cmd = arg_names[i] + "="
        for j in range(len(arg_values)):
            one_cmd += arg_values[j][i] + "#"
        one_cmd = one_cmd[:-1]
        cmd += one_cmd + "&"

    # get ISO information, add by cuilei, May 2016
    # cmd += "storage0[ISO]="
    # iso_dir = config_vstore["iso_path"]
    # iso_names = os.listdir(iso_dir)
    # iso_string = ""
    # for one_iso in iso_names:
    #    iso_string += one_iso + "|"
    # cmd += iso_string + '&'

    cmd += "\" -H \"Accept: text/xml\" " + send_url
    logger.info("cmd: %s" % cmd)

    os.system(cmd)


# 监控后台守护进行运行
def do_monitor_daemon():
    logger.info('***** do_monitor_daemon is running *****')
    try:
        check_daemon_result = commands.getstatusoutput('ps aux | grep hicloud-daemon')[1].split('\n')
        logger.info('check_daemon_result value: %s' % check_daemon_result)
        # 正常情况应该有三条结果
        if len(check_daemon_result) < 3:
            check_port_result = commands.getstatusoutput('netstat -npl | grep 8080')
            logger.info('check_port_result value: %s' % repr(check_port_result))
            if check_port_result[1].strip() == '':
                os.system('/etc/init.d/hicloud-daemon start')
                logger.info('execute hicloud-daemon start')
            else:
                is_restart_daemon = False
                while True:
                    items = commands.getstatusoutput('netstat -npl | grep 8080')[1].split()[-1].strip().split('/')
                    # 出现非后台占用8080端口时，杀掉该进程，执行后台程序重启
                    if items[1].strip() != 'python':
                        # 非后台进程占用8080端口
                        os.system('kill %s' % items[0])
                        is_restart_daemon = True
                    else:
                        running_process = commands.getstatusoutput('ps %s' % items[0])[1].split('/usr/bin/python')[-1]
                        if running_process.strip() != '/usr/sbin/hicloud-daemon':
                            # 非正常python进程占用8080端口
                            os.system('kill %s' % items[0])
                            is_restart_daemon = True
                        else:
                            # 运行状态正常
                            break
                if is_restart_daemon:
                    os.system('/etc/init.d/hicloud-daemon restart')
                    logger.info('execute hicloud-daemon restart')
    except Exception as e:
        logger.error('do_monitor_daemon is error: %s' % repr(e))


# This is the entry when invoked by /usr/bin/hicloud-monitor script
def main():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    try:
        check_pid_file(pid_file)
    except:
        logger.info('another instance is already running, exit')
        return

    with open(pid_file, "w") as fd:
        pid = os.getpid()
        if pid:
            fd.write(str(pid))

    fd.close()

    do_vstore_monitor(sys.argv)
    # do_vmc_monitor(sys.argv)

    config_monitor = Config.load(config_monitor_path)
    if len(config_monitor['portal_url'].strip()) != 0:
        logger.info("begin to do_main")
        do_vmc_monitor(sys.argv)
    else:
        logger.info("stop monitor")

    do_monitor_daemon()
    logger.info('hicloud-monitor is finished')


# This is the entry when running as a standalone module
if __name__ == "__main__":
    main()
