# -*- coding: utf-8 -*-

import os
import posixpath
import time
import urllib
from wsgiref.handlers import SimpleHandler

import urlparse
from SOAPpy import ThreadingSOAPServer, SOAPRequestHandler
from SimpleHTTPServer import SimpleHTTPRequestHandler

import Logging
from WSGISample import application as wsgi_sample_app

from tryServerclass import *

logger = Logging.get_logger("hicloud.core.HTTPServer")


class MixedHTTPRequestHandler(SOAPRequestHandler, SimpleHTTPRequestHandler):
    # do_POST like SOAP Request Handler
    do_POST = SOAPRequestHandler.do_POST

    # do_GET like File HTTP Handler
    do_GET = SimpleHTTPRequestHandler.do_GET
    do_HEAD = SimpleHTTPRequestHandler.do_HEAD
    date_time_string = SimpleHTTPRequestHandler.date_time_string

    # serving static files under directory 'www_dir'
    def translate_path(self, path):
        try:
            if not hasattr(self, 'extension_inited'):
                self.extensions_map['.ovpn'] = 'application/x-openvpn'
                self.extensions_map['.hicloud'] = 'application/x-hicloud-vpn'
                self.extension_inited = True
        except Exception as e:
            logger.exception(e)

        path = urlparse.urlparse(path)[2]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = self.server.www_dir

        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path

    # server WSGI app stored in server.wsgi_mods
    def get_environ(self, prefix):
        env = self.server.base_environ.copy()
        env['SERVER_PROTOCOL'] = self.request_version
        env['REQUEST_METHOD'] = self.command
        if '?' in self.path:
            path, query = self.path.split('?', 1)
        else:
            path, query = self.path, ''

        env['SCRIPT_NAME'] = prefix
        env['PATH_INFO'] = urllib.unquote(path)[len(prefix):]
        env['QUERY_STRING'] = query

        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = host
        env['REMOTE_ADDR'] = self.client_address[0]

        if self.headers.typeheader is None:
            env['CONTENT_TYPE'] = self.headers.type
        else:
            env['CONTENT_TYPE'] = self.headers.typeheader

        length = self.headers.getheader('content-length')
        if length:
            env['CONTENT_LENGTH'] = length

        for h in self.headers.headers:
            k, v = h.split(':', 1)
            k = k.replace('-', '_').upper()
            v = v.strip()
            if k in env:
                continue  # skip content length, type,etc.
            if 'HTTP_' + k in env:
                env['HTTP_' + k] += ',' + v  # comma-separate multiple headers
            else:
                env['HTTP_' + k] = v
        return env

    def get_stderr(self):
        return sys.stderr

    def handle_one_request(self):
        self.raw_requestline = self.rfile.readline()
        if not self.raw_requestline:
            self.close_connection = 1
            return
        if not self.parse_request():  # An error code has been sent, just exit
            return

        for prefix in self.server.wsgi_mods:
            if self.path.startswith(prefix):
                logger.debug('before wsgi SimpleHandler')
                try:
                    handler = SimpleHandler(self.rfile, self.wfile, self.get_stderr(), self.get_environ(prefix))
                    handler.request_handler = self
                    handler.run(self.server.wsgi_mods[prefix])
                except Exception as e:
                    logger.exception(e)
                logger.debug('after wsgi SimpleHandler')
                return

        mname = 'do_' + self.command
        if not hasattr(self, mname):
            self.send_error(501, "Unsupported method (%r)" % self.command)
            return
        method = getattr(self, mname)
        method()


class MixedHTTPServer(ThreadingSOAPServer):

    def __init__(self, endpoint, www_dir=""):
        ThreadingSOAPServer.__init__(self, endpoint, MixedHTTPRequestHandler)
        self.www_dir = www_dir
        self.wsgi_mods = {'/sample_wsgi': wsgi_sample_app}
        self.__endpoint = endpoint

    def server_bind(self):
        """Override server_bind to store the server name."""
        ThreadingSOAPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_address[0]
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = self.server_address[1]
        env['REMOTE_HOST'] = ''
        env['CONTENT_LENGTH'] = ''

    def serve_loop(self, num_request=None):
        logger.info('start serving on (%s, %d)' % self.__endpoint)
        n = 0
        while n != num_request:
            try:
                self.handle_request()
                n += 1
            except Exception as e:
                logger.exception(e)
                logger.info('daemon internal error (%s)', str(e))
                time.sleep(1)
            except BaseException as e:
                logger.info('interrupted by user (%s). exit loop', str(e))
                return
        logger.info('exit normally')

    def register_soap_module(self, soap, path):
        logger.debug('register soap module %s at url path %s', soap, path)
        self.registerObject(soap, path=path)

    def register_wsgi_module(self, app, path):
        logger.debug('register wsgi module %s at url path %s', app, path)
        self.wsgi_mods[path] = app


def tryHTTPServer():
    import sys
    from SOAPpy import SOAPProxy

    # Start Server: python hicloud.core/http.py -s
    if len(sys.argv) == 2 and sys.argv[1] == '-s':
        listen_port = ('172.20.0.235', 8080)
        server = MixedHTTPServer(listen_port, '')


        class Test1:
            def func1(self):
                return 'Test1 func1'


        class Test2:
            def func2(self):
                return 'Test2 func2'

            def func1(self):
                return 'Test2 func1'


        server.register_soap_module(Test1(), path='test1')
        server.register_soap_module(Test2(), path='test2')
	server.register_soap_module(tryServerclass(),path='tryServerclass')
        server.serve_loop()

    # Run Client: python hicloud.core/http.py
    else:
        proxy = SOAPProxy("http://localhost:8080/test2")
        logger.info(proxy.func1())  # Test2 func1
        logger.info(proxy.func2())  # Test2 func2
        proxy = SOAPProxy("http://localhost:8080/test1")
        logger.info(proxy.func1())  # Test1 func1

        # this call should fail
        logger.info(proxy.func2())
