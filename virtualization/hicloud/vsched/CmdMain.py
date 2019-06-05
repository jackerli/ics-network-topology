#!/usr/bin/python

from core import Config, project_path
from core import Logging
from vsched import Model
from vsched.Controller import JobDispatcher


def tryMain():
    logger = Logging.get_logger('hicloud.vsched.CmdMain')  #format=log_format)
    print "debug1"
    config = Config.load(project_path('/tmp/adtp-master/hicloud/vsched.yaml'))
    print "debug2"
    Session = Model.get_ScopedSession(config['connect_string'])
    print "thread_num: %s"%str(config['thread_num'])
    print "debug_soap: %s"%str(config['debug_soap'])
    jobdispatcher = JobDispatcher(
        Session,
        thread_num=config['thread_num'],
        debug_soap=config['debug_soap']
    )
    print "debug2"
    logger.info("Thread job starts")
    jobdispatcher.start()

    while True:
        print('press `q` to quit')

        try:
            cmd = raw_input()
        except:
            break

        if cmd == 'q':
            break
        try:
            lvl = int(cmd)
            logger.setLevel(lvl)
        except:
            pass

    jobdispatcher.stop()
    jobdispatcher.join()
main()
