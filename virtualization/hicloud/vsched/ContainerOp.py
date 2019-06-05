from core import Logging

logger = Logging.get_logger('hicloud.vsched.ContainerOp')


class DummySOAPProxy:
    def __init__(self, url):
        self.url = url

    def __getattr__(self, name):
        def __call_logger(*args, **kwargs):
            logger.debug("called DummySOAPPRoxy(%s) %s%s", self.url, name, str(args))

        return __call_logger


def get_vmc_url(server_name, port=8080):
    return 'http://%s:%d/vmc' % (server_name, port)


def get_vsr_url(server_name, port=8080):
    return 'http://%s:%d/vswitch' % (server_name, port)


def get_webfarm_url(server_name, port):
    return 'http://%s:%d/webfarm' % (server_name, port)
