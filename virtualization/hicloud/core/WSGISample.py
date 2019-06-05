# -*- coding: utf-8 -*-

import cgi
import os

import Logging

logger = Logging.get_logger("hicloud.core.WSGISample")


class WSGISample:

    def __base_url(self, environ):
        return 'http://' + environ['HTTP_HOST'] + environ['SCRIPT_NAME']

    def __this_url(self, environ):
        return 'http://' + environ['HTTP_HOST'] + environ['SCRIPT_NAME'] + environ['PATH_INFO']

    def notfound(self, environ, start_response):
        status = '404 Not Found'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        path_info = environ['PATH_INFO']
        content = ["Page %s not found !" % path_info]
        return content

    def __style(self):
        return '''<style type="text/css">
body {
  font-size: 1em;
  font-family: monospace;
}
h1 {
  text-align: center;
}
div.center {
  width: 600px;
  margin: 0px auto;
}
table {
  width: 600px;
  margin: 0px auto;
  border-width: 1px;
  border-style: solid;
  border-color: gray;
  border-collapse: collapse;
}
th, td {
  border-width: 1px;
  padding: 1px;
  border-style: solid;
  border-color: gray;
}
</style>\n'''

    def listdir(self, environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type', 'text/html')]
        start_response(status, response_headers)

        root_dir = '/'  # FIXME this is dangerous
        path = root_dir

        params = cgi.parse_qs(environ['QUERY_STRING'])
        if params.has_key('path') and params['path']:
            path = os.path.join(path, params['path'][0])

        content = []
        content.append('''<html>
<head>
<title>Index Page</title>
%s
</head>
<body>
<h1>Listdir %s Page</h1>
<table>
<th>name</th><th>type</th></tr>\n''' % (self.__style(), path))

        if path != root_dir:
            parent = os.path.split(path)[0]
            url = self.__this_url(environ) + "?path=" + parent
            content.append('<tr><td><a href="%s">..</a></td><td>up level directory</td></tr>\n' % url)

        for file in os.listdir(path):
            fpath = os.path.join(path, file)
            ftype = os.popen('file -b %s' % fpath).read()
            if os.path.isdir(fpath):
                url = self.__this_url(environ) + "?path=" + fpath
                content.append('<tr><td><a href="%s">%s</a></td><td>%s</td></tr>\n' % (url, file, ftype))
            else:
                content.append('<tr><td>%s</td><td>%s</td></tr>\n' % (file, ftype))

        content.append('</table>\n</body>\n</html>')
        return content

    def index(self, environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type', 'text/html')]
        start_response(status, response_headers)

        content = []
        content.append('''<html>
<head>
<title>Index Page</title>
%s
</head>
<body>
<h1>Index Page</h1>
<div class="center">
<ul>\n''' % self.__style())

        for method in dir(self):
            if method.startswith('_'):
                continue
            content.append('<li><a href="%s">%s</a></li>\n' % (method, method))
        content.append('</ul>\n</body>\n</html>')

        return content

    def info(self, environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type', 'text/html')]
        start_response(status, response_headers)

        x = 'WSGI Info\n\n'
        content = []
        content.append('''<html>
<head><title>WSGI Info</title>
%s
</head>
<body>
<h1>WSGI Info</h1>
<table>
<th>name</th><th>value</th></tr>\n''' % self.__style())

        items = environ.items()
        items.sort()
        for k, v in items:
            content.append('<tr><td>%s</td><td>%s</td></tr>\n' % (k, v))

        content.append('</table>\n</body>\n</html>')
        return content

    def __redirect(self, target, environ, start_response):
        status = '301 Moved Permanently'
        location = self.__base_url(environ) + target
        response_headers = [
            ('Content-type', 'text/plain'),
            ('Location', location)
        ]
        start_response(status, response_headers)

        content = ['Requested page moved to: ' + location]
        return content

    def __call__(self, environ, start_response):
        logger.debug('entering wsgi sample')

        try:
            path_info = environ['PATH_INFO']
            if not path_info.startswith('/'):
                content = self.__redirect('/' + path_info, environ, start_response)

            path_info = path_info.strip('/')
            if not path_info:
                path_info = 'index'

            if hasattr(self, path_info):
                content = getattr(self, path_info)(environ, start_response)
            else:
                content = self.notfound(environ, start_response)
        except Exception as e:
            logger.exception(e)

        logger.debug('exiting wsgi sample app')
        return content


application = WSGISample()
