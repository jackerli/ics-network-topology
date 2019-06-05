# -*- coding: utf-8 -*-

import logging
import logging.handlers

import Config

config_daemon_path = str("/vmc160/hicloud/daemon.yaml")
config = Config.load(config_daemon_path)

level2name = {
    'notset': 0,
    'debug': 10,
    'info': 20,
    'warning': 30,
    'error': 40,
    'critical': 50
}
log_level = level2name.get(config.get('log_level_name', 'debug'), logging.DEBUG)
# 配置文件里面是以MB为单位，默认日志大小为10M
log_max_size = config.get('log_max_size', '10') * 1024 * 1024
backup_count = config.get('backup_count', '50')


def get_logger(name, filename='/tmp/hicloud_server.log',
               format='%(asctime)s %(levelname)-8s %(name)s %(lineno)d %(threadName)s %(message)s',
               level=log_level, default=False):
    logger = logging.getLogger(name)

    if filename:
        handler = logging.handlers.RotatingFileHandler(filename)
        handler.setFormatter(logging.Formatter(format, '%Y-%m-%d %H:%M:%S'))
        # 设置日志文件的最大大小（单位字节）
        handler.maxBytes = log_max_size
        # 设置最大备份文件数量，超过最大备份数量后，将从前边进行翻转录入（从前往后重写这些文件）
        handler.backupCount = backup_count
        if default:
            logging.root.addHandler(handler)
        else:
            logger.addHandler(handler)
    else:
        raise Exception("No log file has been given!!!")

    if default:
        logging.root.setLevel(level)
    else:
        # 显示大于等于该级别的日志信息
        logger.setLevel(level)
    return logger
