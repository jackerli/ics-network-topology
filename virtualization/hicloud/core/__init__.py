# -*- coding: utf-8 -*-

__version__ = "2.0+r8212+20110222"
import os

rundebug = False
project_dir = ''


def set_rundebug():
    global rundebug
    rundebug = True
    global project_dir
    project_dir = os.getcwd()


def is_rundebug():
    return rundebug


def project_path(filename):
    if is_rundebug() and filename[0] == '/':
        filename = '%s/data%s' % (project_dir, filename)
        if filename.endswith('.yaml'):
            devfn = filename[:-5] + '-dev.yaml'
            if os.path.exists(devfn):
                return devfn
    return filename
