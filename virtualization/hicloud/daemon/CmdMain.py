# -*- coding: utf-8 -*-

import os
import signal
import sys
import Config
import Logging
import Utils
import commands
from HTTPServer import MixedHTTPServer


class DummyServer:
    def __init__(self, *args):
        pass


daemon_plugins = {
    'vmc': "vmc.Plugin",
    # vstore doesn't have an SOAP interface, but it needs http GET to serve rootfs
    #'vsched': "hicloud.vsched.Plugin"
}


class ExitSignal(BaseException):
    pass


def make_signal_handler(logger, config):
    def __signal_handler(signum, frame):
        logger.info('caught signal: %d, daemon exiting...', signum)
        raise ExitSignal('signal: %d' % signum)

    return __signal_handler


def do_server(logger, config, argv):
    # probe external address
    # 获取服务器IP
    #python CmdMain.py  kill the daemon
    enabled_caps = []
    if len(argv) == 1:
	 for cap in enabled_caps:
         	try:
            		logger.debug('fini capability: %s' % cap)
            		daemon_plugins[cap].fini()
        	except Exception as e:
            		logger.exception(e)
            		logger.error('error fini capability: %s (%s)', cap, str(e))

    		logger.info('daemon exit')
         return
    else:
         if len(argv)!=2:
                return

    '''
    if not config['external_address']:
        logger.info('no external address defined in daemon config file')
        addr = Utils.external_address()
        logger.info('probed external address: %s', addr)
        config['external_address'] = addr
    '''
    #python CmdMain.py -s
    if not config['listen_address']:
        listen_address = ''
    else:
        listen_address = config['listen_address']  # add by cuilei, May 2016

    endpoint = (listen_address, config['listen_port'])
    logger.info('daemon listen address and port: %s' % repr(endpoint))

    logger.info('daemon initializing...')
    server = MixedHTTPServer(endpoint=endpoint)
 
    # validate capabilities
    caps = config['capabilities']
    logger.debug('capabilities: %s' % repr(caps))
    if type(caps) != list:
        logger.error('bad capabilities. reset it to empty')
        caps = []

    # init capabilities
    # 加载系统模块
    enabled_caps = []
    for cap in caps:
        if not daemon_plugins.has_key(cap):
            logger.error('wrong capabilities: %s' % cap)
            continue
        try:
            logger.debug('init capability: %s' % cap)
            temp_plugin = daemon_plugins[cap]
            tempList = temp_plugin.split('.')
            parent_plugin = tempList[0]
            plugin = tempList[1]
            if type(plugin) == str:
                exec('from '+parent_plugin+' import ' + plugin)
                daemon_plugins[cap] = eval(plugin)
                logger.info('load capability from file: %s' % eval(plugin).__file__)
            daemon_plugins[cap].init()
        except Exception as e:
            logger.exception(e)
            logger.error('error init capability: %s (%s)', cap, str(e))
            continue

        # 将初始化模块中的方法引入到SOAPProxy代理中
        for path, mod in daemon_plugins[cap].soap_mods().items():
            logger.info("mod: %s, path: %s" % (mod, path))
            server.register_soap_module(mod, path)

        enabled_caps.append(cap)
        logger.info('enabled capability: %s' % cap)

    logger.info('daemon initialized')
    server.serve_loop()
    logger.info('daemon cleaning...')

def getPort(logger):
    logger.info("getPort is running")
    try:
	current_pid_num = os.getpid()
	logger.info("cur:%s"%(str(current_pid_num)))
	command = "ps -a|grep python"
        ret = commands.getstatusoutput(command)
	logger.info("result of %s is:%s"%(command, ret[0]))
	logger.info(ret[1])
	if ret[0] == 0:
        	res = ret[1].split("\n")	
		for re in res:
			pid_num = re.split(" ")[0]
			logger.info("%d %d"%(len(str(current_pid_num)), len(pid_num)))
			if pid_num.strip() != str(current_pid_num).strip():
				logger.info("fuck")
				command = "kill -9 %s"%(str(pid_num))
		        	ret = commands.getstatusoutput(command)
        			logger.info("result of %s is:%s"%(command, ret[0]))
			else:
				logger.info("not kill itself with pid:%s"%(str(current_pid_num)))
    except Exception as e:
    	logger.error("error in getPort:%s"%(str(e)))

def main(argv):
    # daemonized itself at very begining
    # 创建一个子进程（守护进程或者叫后台进程），并退出父进程
    '''
    if Utils.daemonize():
        # parent process exit
        exit(0)
    '''
    # now run in daemon mode
    
    # load config and initialize logger
    config_file = '/vmc160/hicloud/daemon.yaml'
    try:
        config = Config.load(config_file)
        logger = Logging.get_logger('hicloud.daemon.CmdMain',config['log_file'])
	#getPort(logger)
    except Exception as e:
        # steal logger of Config since we don't have one yet
        Config.logger.exception(e)
        Config.logger.fatal('Error in config %s:\n    %s' % (config_file, e))
        exit(1)

    for k, v in config.items():
        if type(v) == str:
            logger.debug('config var: %s = %s', k, v)

    # run server code
    try:
        do_server(logger, config, argv)
    except Exception as e:
        logger.exception(e)
        logger.fatal('internal error. daemon exit')

main(sys.argv)

