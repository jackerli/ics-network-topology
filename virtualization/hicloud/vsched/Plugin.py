from hicloud.core import Config, project_path
from hicloud.core import Logging
from hicloud.vsched import Model
from hicloud.vsched.Controller import JobDispatcher, InitMountJob, MonitorLicense
from hicloud.vsched.Server import ServerClass

logger = Logging.get_logger('hicloud.vsched.Plugin')

__obj = None
__jobdispatcher = None
__initMountJob = None
__monitorLicenseJob = None


def init(daemon_config):
    config = Config.load(project_path('/etc/hicloud/vsched.yaml'))
    # this should dispatch 'hicloud.vsched.*' to individual log file
    Logging.get_logger('hicloud.vsched', filename=config['log_file'])
    # after logger initialzed, register Model obj debug formatter
    Model.register_generic_repr()

    logger.debug('initializing %s(soap)' % __name__)
    global __obj
    if __obj:
        logger.error('reinitialized is not supported')
        return
    __obj = ServerClass(config)

    logger.debug('initializing %s(controller)' % __name__)
    Session = Model.get_ScopedSession(config['connect_string'])

    global __jobdispatcher
    __jobdispatcher = JobDispatcher(
        Session,
        thread_num=config['thread_num'],
        debug_soap=config['debug_soap'],
        task_timeout=config['task_timeout'],
    )
    __jobdispatcher.start()

    global __initMountJob
    __initMountJob = InitMountJob()
    __initMountJob.start()

    global __monitorLicenseJob
    __monitorLicenseJob = MonitorLicense()
    __monitorLicenseJob.start()


def fini():
    global __obj
    del __obj

    global __jobdispatcher
    __jobdispatcher.stop()
    __jobdispatcher.join()

    global __initMountJob
    __initMountJob.stop()

    global __monitorLicenseJob
    __monitorLicenseJob.stop()


def soap_mods():
    global __obj
    return {'vsched': __obj}


def wsgi_mods():
    return {}
