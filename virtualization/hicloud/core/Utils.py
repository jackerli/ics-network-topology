# -*- coding: utf-8 -*-

import errno
import re
import socket
import struct
import uuid

import fcntl

from core import Logging

logger = Logging.get_logger('hicloud.core.Utils')

__strstrip_fmt = re.compile('[ \t\n\r]+')


def string_trim(str, length=30):
    if not str:
        return str

    # 将字符串中的指定字符替换为单个空格
    newstr = __strstrip_fmt.sub(' ', str)
    if len(newstr) > length:
        return newstr[:length - 3] + '...'
    return newstr


def GenUUID():
    return str(uuid.uuid1())


# 获取网关对应机器的IP
def interface_address(iface):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', iface[:15])
    )[20:24])


class NoExternalAddress(Exception):
    pass


def external_address():
    try:
        logger.debug('start hostname probing')
        # 获取服务器域名
        hostname = socket.gethostname()
        logger.debug('possible hostname: %s' % hostname)
        # 获取域名对应的host地址列表
        hostinfo = socket.gethostbyaddr(hostname)
        logger.debug('probed hostinfo: %s' % repr(hostinfo))
        if hostname != hostinfo[0]:
            logger.debug('hostname probing failed (hostinfo mismatch)')
        else:
            logger.debug('confirmed hostname: %s', hostname)
            addrs = hostinfo[2]
            logger.debug('possible addresses: %s' % addrs)
            addr = addrs[0]  # get first addr
            if addr.split('.')[0] != '127':
                logger.debug('confirmed address: %s' % addr)
                return addr  # return non-loop first addr
            logger.debug('hostname probing failed (loop address: %s)' % addr)
    except Exception as e:
        logger.exception(e)
        logger.info('hostname probing failed: %s' % str(e))

    try:
        logger.debug('continue route table probing')
        piface = None
        # find primary interface according to default route
        lines = open('/proc/net/route').readlines()
        logger.debug('probing /proc/net/route: %d lines', len(lines))
        for line in lines[1:]:
            tokens = line.split()
            if len(tokens) != 11:
                logger.debug('non standard route line: %s' % line)
                continue
            if not piface:
                piface = tokens[0]
                logger.debug('possible primary interface: %s' % piface)
            if tokens[1] == "00000000" and tokens[7] == "00000000":
                piface = tokens[0]
                logger.debug('confirmed primary interface (default route): %s' % piface)
        addr = interface_address(piface)
        logger.debug('primary interface and address: %s %s', piface, addr)
        return addr
    except Exception as e:
        logger.exception(e)
        logger.info('route table probing failed: %s' % str(e))
        raise NoExternalAddress('Unable to get external address')


# copy & paste from old daemon
import os
import resource


def close_all():
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        maxfd = 1024

    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:
            pass


def get_devnull():
    if (hasattr(os, "devnull")):
        return os.devnull
    else:
        return "/dev/null"


def daemonize():
    # 创建一个子进程，并获取父进程ID
    pid = os.fork()
    if pid != 0:
        return pid

    # 将刚才创建的子进程设置为父进程
    os.setsid()
    # signal.signal(signal.SIGHUP, signal.SIG_IGN)
    # 创建真正的守护进程
    pid = os.fork()

    # 退出第一次创建的子进程
    if pid != 0:
        os._exit(0)

    close_all()
    os.open(get_devnull(), os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)
    return 0


class PidExistsError(Exception):
    pass


def check_pid_file(pid_file):
    logger.info('***** check_pid_file is running *****')
    if not os.path.exists(pid_file):
        logger.debug('pid file %s not exist. pid_file_check passed', pid_file)
        return
    logger.debug('pid file %s exists', pid_file)

    try:
        # if exists but unable to read, raise
        pid_fd = open(pid_file)
        logger.debug('pid file %s opened', pid_file)
        # if exists but unable to find an integer, raise
        pid = int(pid_fd.read().strip())
    except Exception as e:
        logger.debug('pid file %s error: %s', pid_file, str(e))
        raise PidExistsError('pid file error: %s' % str(e))

    # test if pid is alive
    try:
        logger.debug('try kill pid=%d, signal=0' % pid)
        os.kill(pid, 0)
        logger.debug('process (pid=%d) alive and owned by current user' % pid)

        # 当前设置监控间隔为三分钟，如果三分钟仍然没有执行完，强制杀掉
        os.kill(pid, 9)
        logger.info('!!!!! force kill hicloud-monitor pid: %s !!!!!' % pid)
    #        # hit here means pid is alive
    #        raise PidExistsError, 'process (pid=%d) still running' % pid
    except OSError as e:
        # hit here can be of two reasons
        #  1. pid exists but not owned by us, raise
        if e.errno == errno.EPERM:
            logger.debug('process (pid=%d) run by other user' % pid)
            raise PidExistsError('pid exists')
        #  2. pid not exists, pass
        elif e.errno == errno.ESRCH:
            logger.debug('process not exist')
            return
        else:
            logger.error('kill hicloud-monitor pid error: %s' % e.message)
            return


def run_daemon(cmd_list, workdir, pid_file):
    pid = daemonize()
    if pid != 0:  # not child
        os.waitpid(pid, 0)
        return

    with open(pid_file, 'w') as fd:
        pid = os.getpid()
        if pid:
            fd.write(str(pid))

    os.chdir(workdir)
    os.umask(0)

    os.execv(cmd_list[0], cmd_list)
    exit(0)


def calculateNetwork(ip, netmask):
    try:
        ip1 = struct.unpack('I', socket.inet_aton(ip))[0]
        netmask1 = struct.unpack('I', socket.inet_aton(netmask))[0]
        network = socket.inet_ntoa(struct.pack('I', ip1 & netmask1))
        return network
    except:
        return '0.0.0.0'


def generateAddress(network, hostid):
    try:
        network1 = struct.unpack('I', socket.inet_aton(network))[0]
        hostid1 = struct.unpack('I', socket.inet_aton('0.0.0.%d' % hostid))[0]
        address = socket.inet_ntoa(struct.pack('I', network1 | hostid1))
        return address
    except:
        return '0.0.0.0'
