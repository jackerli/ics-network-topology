import os

os.environ['python_egg_cache'] = '/tmp/'

import sys

sys.stdout = sys.stderr

import atexit

# delete SIGTERM before importing cherrypy, so cherrypy won't register signal handler
import signal

tmp = signal.SIGTERM
del signal.SIGTERM
import cherrypy

signal.SIGTERM = tmp

import cherrypy._cpwsgi
import turbogears

from hicloud.core import Logging

logger = Logging.get_logger('hicloud.daemon.VMCWebPlugin')

try:
    import vmcweb.controllers
except:
    sys.path.append(
        os.getcwd() + '/vmcweb')  # must add full path to sys.path, otherwise cherrypy static_filter stops working
    import vmcweb.controllers


def init(daemon_config):
    turbogears.update_config(configfile="dev.cfg", modulename="vmcweb.config")
    turbogears.config.update({'global': {'server.environment': 'production'}})
    turbogears.config.update({'global': {'autoreload.on': False}})
    turbogears.config.update({'global': {'server.log_to_screen': False}})
    turbogears.config.update({'global': {'server.webpath': '/vmcweb'}})
    cherrypy.root = vmcweb.controllers.Root()

    if cherrypy.server.state == 0:
        cherrypy.server.start(init_only=True, server_class=None)
        atexit.register(cherrypy.server.stop)


def fini():
    pass


def soap_mods():
    return {}


def application(environ, start_response):
    environ['SCRIPT_NAME'] = ''
    return cherrypy._cpwsgi.wsgiApp(environ, start_response)


def wsgi_mods():
    return {'/vmcweb': application}
