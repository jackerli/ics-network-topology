#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
1.HACheck作为独立进程运行在VMC所在机器，担当2种角色之一：master(接收slave心跳)，slave(向master发送心跳)；
2.HACheck要实现以下功能：
    A.分布式环境下，基于socket的心跳发送和接收
    B.不存在master节点时，在slave节点之间选举master节点
    C.若存在多个master节点，在多个master节点之间决策1个master节点 
    D.master失效时，slave要能识别，从而发起选举master的动作
    E.slave失效时，master要能识别，从而发起迁移虚拟机的动作
    F.主机间传递的消息经过加密 
    G.通过广播找到同一网段的其他HA节点 
'''

import base64
import datetime
import os
import pickle
import signal
import socket
import struct
import subprocess
import sys
import threading
import time

import Queue
import fcntl
from SOAPpy import *

from hicloud.core import Config
from hicloud.core import Logging
from hicloud.core import project_path

logger = Logging.get_logger('hicloud.vmc.HACheck', '/var/log/hicloud/hacheck.log')


class Utility(object):
    # define constant variables #
    TYPE_SYNCHRONIZE = -3
    TYPE_REPORT = -2
    TYPE_DISCOVERY = -1
    TYPE_HEARTBEAT = 0
    TYPE_ELECTION = 1

    ROLE_MASTER = 'M'
    ROLE_SLAVE = 'S'
    ROLE_UNKNOWN = 'U'
    ROLE_MANAGER = 'm'

    STATUS_LOST = 'N'
    STATUS_LIVE = 'Y'
    STATUS_DEAD = 'D'

    VALUE_MASTER = 10000
    VALUE_SLAVE = -1

    @staticmethod
    def shell(command, timeout=10):
        rtn = None
        try:
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            t0 = datetime.datetime.now()
            while p.poll() is None:
                if (datetime.datetime.now() - t0).seconds < timeout: continue
                os.kill(p.pid, signal.SIGKILL)
                os.waitpid(-1, os.WNOHANG)
                break
            if p.returncode == 0:
                rtn = p.stdout.readlines()
            elif p.returncode is not None:
                raise Exception("@shell(%s), error: %s" % (command, str(p.stderr.readlines())))
        except Exception as e:
            logger.exception(e)
        return rtn

    @staticmethod
    def get_free_memory():
        try:
            rtn = Utility.shell("cat /proc/meminfo")
            return int(rtn[1].split()[1])  # MemFree: 24591072 kB
        except Exception as e:
            logger.exception(e)
        return 0

    @staticmethod
    def get_if_ip(ifname):
        tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            tmp.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])


class Message(object):
    def __init__(self, src, dest, role, type, value):
        self.src, self.dest, self.role, self.type, self.value = src, dest, role, type, value

    def __str__(self):
        return ('Message: %s:%s->%s:%s, role=%s, type=%s, value=%s' % (str(self.src[0]), str(self.src[1]),
                                                                       str(self.dest[0]), str(self.dest[1]),
                                                                       str(self.role), str(self.type), str(self.value)))


class MessageCenter(threading.Thread):
    def __init__(self, owner):
        threading.Thread.__init__(self)
        self.owner = owner
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.bind(owner.bind)
        self.socket.settimeout(10)  # 10 seconds
        self.q0 = Queue.Queue()
        self.q1 = Queue.Queue()
        self.receiver = MessageCenter.Receiver(self)
        self.count = 0

    class Receiver(threading.Thread):
        def __init__(self, owner):
            threading.Thread.__init__(self)
            self.owner = owner

        def run(self):
            while self.owner.owner.running:
                try:
                    bytes, address = self.owner.socket.recvfrom(2048)
                    message = pickle.loads(base64.b64decode(str(bytes)))
                    message.src = address
                    self.owner.count += 1
                    self.owner.q0.put(message)
                except socket.timeout:
                    pass
                except Exception as e:
                    logger.exception(e)

    def run(self):
        self.receiver.start()
        while self.owner.running:
            self.__receiveMessage()
            self.__sendMessage()
        else:
            self.socket.close()

    def __sendMessage(self):
        try:
            message = self.q1.get(True, 1)  # 1 seconds
            self.socket.sendto(base64.b64encode(pickle.dumps(message)), message.dest)
        except Queue.Empty:
            pass
        except Exception as e:
            logger.exception(e)

    def __receiveMessage(self):
        try:
            message = self.q0.get(True, 1)  # 1 seconds
            if message and message.src != message.dest:
                self.owner.receiveMessage(message)
        except Queue.Empty:
            pass
        except Exception as e:
            logger.exception(e)

    def sendMessage(self, message):
        if message and message.src != message.dest:
            self.q1.put(message)


class Agent(threading.Thread):
    def __init__(self, cluster):
        threading.Thread.__init__(self)
        self.cfg = Config.load(project_path("/etc/hicloud/ha.yaml"))
        self.bind = '', int(self.cfg['port'])  # bind all interfaces
        self.cluster = cluster
        self.role = Utility.ROLE_UNKNOWN
        self.value = Utility.get_free_memory()
        self.master = None
        self.managers = set()
        self.nodes = set()
        self.tickets = {}
        self.heartbeats = {}
        self.timestamps = {}  # 记录运行时数据的最后更新时间
        self.mc = MessageCenter(self)
        self.t0 = datetime.datetime.now()
        self.running = True
        self.runtime = 1

    def __str__(self):
        return ('Agent: managers=%s, nodes=%s, cluster=%s, master=%s, tickets=%s, heartbeats=%s, runtime=%s' %
                (str(self.managers), str(self.nodes), str(self.cluster), str(self.master),
                 str(self.tickets), str(self.heartbeats), str(self.runtime)))

    def receiveMessage(self, message):  # 被动处理消息
        # logger.info(message)
        if message.type == Utility.TYPE_DISCOVERY:  # 检测其他HA节点
            if message.value == self.cluster:  # 同一个cluster的节点给予响应
                if message.dest[0] == '<broadcast>':
                    self.mc.sendMessage(
                        Message(self.bind, message.src, self.role, Utility.TYPE_DISCOVERY, self.cluster))  # 我是HA节点
                if message.role == Utility.ROLE_MANAGER:  # 对方是管理节点
                    self.managers.add(message.src)
                else:  # 如果不是前两种，那就是主节点或从节点
                    self.nodes.add(message.src)
                    self.timestamps['nodes'] = datetime.datetime.now()

        elif message.type == Utility.TYPE_HEARTBEAT:  # 心跳
            self.heartbeats[message.src] = datetime.datetime.now()
            if self.role == Utility.ROLE_MASTER and message.role == Utility.ROLE_SLAVE:
                self.mc.sendMessage(Message(self.bind, message.src, self.role, Utility.TYPE_HEARTBEAT, self.value))

        elif message.type == Utility.TYPE_ELECTION:  # 主节点选举
            if self.role == Utility.ROLE_MASTER:
                if message.role == Utility.ROLE_MASTER:  # 对方说自己是主节点
                    if message.value > self.t0:
                        for target in self.heartbeats.copy().keys():
                            self.mc.sendMessage(Message(message.src, target, Utility.ROLE_MASTER, Utility.TYPE_ELECTION,
                                                        Utility.VALUE_MASTER))
                        logger.info(
                            '@receiveMessage(), %s is degraded. New Master is %s' % (str(self.bind), str(message.src)))
                        self.role = Utility.ROLE_SLAVE  # 我降级了! ROLE_MASTER -> ROLE_SLAVE
                        self.master = message.src
                        self.tickets = {}
                        self.heartbeats = {}
                    else:
                        self.mc.sendMessage(Message(self.bind, message.src, self.role, Utility.TYPE_ELECTION, self.t0))
                else:  # 对方不是主节点，我告诉它我是主节点
                    self.mc.sendMessage(
                        Message(self.bind, message.src, self.role, Utility.TYPE_ELECTION, Utility.VALUE_MASTER))
                return  # 我自己的角色明确了
            if type(message.value) == int and message.value == Utility.VALUE_MASTER:  # 对方说自己是主节点，那我就是从节点
                self.role = Utility.ROLE_SLAVE
                self.master = message.src
                self.tickets = {}
                self.heartbeats = {}
                self.runtime = 1
                return  # 我自己的角色明确了
            if ((type(message.value) == int and message.value != Utility.VALUE_SLAVE and message.value > self.value) or
                    (type(message.value) == datetime.datetime and message.value > self.t0)):
                self.role = Utility.ROLE_SLAVE  # 若对方比我大，我就是从节点
                self.mc.sendMessage(
                    Message(self.bind, message.src, self.role, Utility.TYPE_ELECTION, Utility.VALUE_SLAVE))
                return  # 我自己的角色明确了
            tmp = self.tickets.get(message.src)
            if (self.runtime == 1 and (tmp is None or tmp != Utility.VALUE_SLAVE) or
                    self.runtime == 2 and (type(tmp) != int or tmp != Utility.VALUE_SLAVE)):
                if self.role == Utility.ROLE_SLAVE and self.master is not None: return  # 已经找到主节点了，就不用ticket了
                self.tickets[message.src] = message.value  # 把它存起来，下次还要问它，没准它就是主节点
                self.timestamps['tickets'] = datetime.datetime.now()

        elif message.type == Utility.TYPE_SYNCHRONIZE:  # 同步节点数据
            if message.value in self.nodes:
                logger.info('@receiveMessage(), Remove unreachable node: :%s!!' % str(message.value))
                self.nodes.remove(message.value)  # 删除失效节点，以便进行隔离判定

    def run(self):  # 主动发送消息
        logger.info('@run(), Agent %s/%s start at %s' % (
            str(self.bind), str(self.cluster), time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
        self.mc.start()
        self.mc.sendMessage(Message(self.bind, ('<broadcast>', self.bind[1]),
                                    self.role, Utility.TYPE_DISCOVERY, self.cluster))  # 启动起来，即检测其他节点
        index = 1
        while (self.running):
            self.check_isolate()
            if index % 60 == 0:  # 定期更新节点数据，以应对分区合并的情况
                self.mc.sendMessage(Message(self.bind, ('<broadcast>', self.bind[1]),
                                            self.role, Utility.TYPE_DISCOVERY, self.cluster))  # 通过广播更新节点数据

            if self.role == Utility.ROLE_MASTER:
                if index % 65 == 0:  # 定期检测其他主节点。要求更新节点数据以后才需要运行。
                    for target in self.nodes.copy():
                        self.mc.sendMessage(Message(self.bind, target, self.role, Utility.TYPE_ELECTION, self.t0))

                if index % 5 == 0:  # 定期向管理节点反馈数据
                    self.report()

                for k, v in self.heartbeats.copy().items():
                    if type(v) != str or v != Utility.STATUS_LOST:
                        if (datetime.datetime.now() - v).seconds > self.delay(5):  # 定期检测节点失效
                            self.heartbeats[k] = Utility.STATUS_LOST
                            if k in self.nodes:
                                for target in self.nodes.copy():  # 通知其他节点，删除失效节
                                    self.mc.sendMessage(
                                        Message(self.bind, target, self.role, Utility.TYPE_SYNCHRONIZE, k))
                                self.nodes.remove(k)  # 删除失效节点，以便进行隔离判定
                            logger.info('@run(), Slave:%s is unreachable!!' % str(k))

            elif self.role == Utility.ROLE_SLAVE:
                if self.master is not None:  # 从节点向主节点发送心跳
                    self.mc.sendMessage(Message(self.bind, self.master, self.role, Utility.TYPE_HEARTBEAT, self.value))

                tmp = self.heartbeats.get(self.master)
                if tmp is not None and (datetime.datetime.now() - tmp).seconds > self.delay(5):  # 定期检测节点失效
                    self.role = Utility.ROLE_UNKNOWN
                    if self.master in self.nodes:
                        for target in self.nodes.copy():  # 通知其他节点，删除失效节点
                            self.mc.sendMessage(
                                Message(self.bind, target, self.role, Utility.TYPE_SYNCHRONIZE, self.master))
                        self.nodes.remove(self.master)  # 删除失效节点，以便进行隔离判定
                    logger.info('@run(), Master:%s is unreachable!!' % str(self.master))
                    self.master = None
                    self.tickets = {}
                    self.runtime = 1
                    self.timestamps = {}

            elif self.role == Utility.ROLE_UNKNOWN:
                if self.runtime == 1:  # 第1次选举
                    for target in self.nodes.copy():
                        tmp = self.tickets.get(target)
                        if tmp is None or tmp != Utility.VALUE_SLAVE:  # 未知或已知对方不是从节点，才需要再发消息
                            self.mc.sendMessage(
                                Message(self.bind, target, self.role, Utility.TYPE_ELECTION, self.value))
                if self.runtime == 2:  # 第2次选举
                    for target, tmp in self.tickets.copy().items():
                        if type(tmp) != int or tmp != Utility.VALUE_SLAVE:  # 未知或已知对方不是从节点，才需要再发消息
                            self.mc.sendMessage(Message(self.bind, target, self.role, Utility.TYPE_ELECTION, self.t0))
                self.elect_master()

            index += 1
            time.sleep(1)  # 1 seconds
        else:
            logger.info('Agent %s/%s stop -> %s' % (str(self.bind), str(self.role), str(self)))

    def stop(self):
        self.running = False

    def delay(self, interval=0):
        return int(self.cfg['delay']) + interval

    def check_isolate(self, timeout=10):  # default 10 seconds
        tmp = time.time()
        while len(self.nodes) <= 1:  # 注意：从这里退出的时候，客户端数据是不完整的，这是为了节省等待的时间
            if time.time() - tmp < timeout: continue  # 延时timeout秒
            # 如timeout秒内没有找到其他节点，判定自己被隔离了
            logger.info('@check_isolate(), %s is isolated!' % str(self.bind))
            if self.role == Utility.ROLE_UNKNOWN and self.heartbeats:  # 如果曾经是SLAVE节点，升级为主节点
                logger.info('@check_isolate(), %s is upgraded as a single master!' % str(self.bind))
                self.role = Utility.ROLE_MASTER  # 我升级了! ROLE_SLAVE -> ROLE_MASTER
                self.master = None
                self.tickets = {}
                self.heartbeats = {}
            return False
        else:
            return True

    def elect_master(self, value=5):  # default 5 seconds
        # 选举时机: 运行时数据呈现稳定状态以后再进行选举
        tmp = datetime.datetime.now()
        if ((self.timestamps.has_key('nodes') and (tmp - self.timestamps['nodes']).seconds > value) and
                (self.timestamps.has_key('tickets') and (tmp - self.timestamps['tickets']).seconds > value)):
            # 选举算法: 如果其他节点都比我小，我就是主节点!
            tmp = filter(lambda x: type(x) == int, self.tickets.values())
            logger.info('@elect_master(), ELECT: %s/%s/%s' % (str(self.nodes), str(self.tickets), str(tmp)))
            if len(self.nodes) - 1 == len(self.tickets) == len(tmp) != 0:
                if tmp and max(tmp) == Utility.VALUE_SLAVE:  # 最大的1个说它是从节点，那我就是主节点
                    logger.info('@elect_master(), %s/%s is the master after %d messages!' % (
                        str(self.bind), str(self.value), self.mc.count))
                    self.role = Utility.ROLE_MASTER
                    for target in self.tickets.copy().keys():
                        self.mc.sendMessage(
                            Message(self.bind, target, self.role, Utility.TYPE_ELECTION, Utility.VALUE_MASTER))
                    self.tickets = {}
                    self.heartbeats = {}
                    self.runtime = 1
                if tmp and max(tmp) == self.value:  # 最大的1个说它和我一样大，那进行第2次选举
                    self.runtime = 2
                    logger.info('@elect_master(), Round 2 election: %s!' % str(self.tickets))

    def report(self):
        try:
            url = "http://" + self.cfg['portal_url'] + ":8080/vsched"
            logger.info('@report(), url: %s' % url)
            soap_invoke = getattr(SOAPProxy(url), "update_ha_info")
            tmp = self.heartbeats.copy()
            for k in tmp.keys():
                if type(tmp[k]) == datetime.datetime: tmp[k] = Utility.STATUS_LIVE
            logger.info('@report(), data: %s' % str(tmp))
            rtn = soap_invoke(repr(Utility.get_if_ip('br0')), repr(self.cluster), repr(tmp))
        except Exception as err:
            logger.error('@report(), exception: %s' % str(err))


# script entry
if __name__ == '__main__':
    instance = Agent(sys.argv[1])  # cluster
    instance.start()
    for tmp in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(tmp, lambda n, f: instance.stop())
    signal.pause()
