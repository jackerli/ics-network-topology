# -*- coding: utf-8 -*-

import posixpath
import re

import yaml

from core import project_dir

class BadFormat(Exception):
    pass


def resolve_config_vars(config, parent=None):
    if parent != None:
        merged_dict = parent.copy()
        merged_dict.update(config)
    else:
        merged_dict = config

    for kk, vv in config.items():
        if type(vv) == dict:
            resolve_config_vars(vv, merged_dict)

        if type(vv) == list:
            for i in range(len(vv)):
                if type(vv[i]) != str:
                    continue
                vv[i] = resolve_config_var(vv[i], merged_dict)
                merged_dict.update(config)

        if type(vv) == str:
            config[kk] = resolve_config_var(vv, merged_dict)
            merged_dict.update(config)


def resolve_config_var(str, dictionary):
    tmpdict = dictionary.copy()
    # find all $(var_name) in string
    var_expr = re.compile(r'\$\(([a-zA-Z_][a-zA-Z0-9_]*)\)')
    # replace item to %(var_name)s
    format_str = var_expr.sub(r'%(\1)s', str)

    # add project_dir to dictionary
    if not 'project_dir' in tmpdict:
        tmpdict['project_dir'] = project_dir

    try:
        # using python builtin string format to resolve var
        newstr = format_str % tmpdict
    except:
        # if we hit here, it means referenced var does not exist in config
        raise BadFormat('"%s" contains unresolvable key' % str)

    while newstr != str:
        str = newstr
        format_str = var_expr.sub(r'%(\1)s', str)
        newstr = format_str % tmpdict

    return newstr


def import_config_files(config, dir):
    try:
        filelist = config['import']
    except:
        filelist = []
    conflist = []
    for filename in filelist:
        confpath = dir + '/' + filename
        import_conf = load(confpath)
        conflist.append(import_conf)

        # remove 'import' from tmp_conf
        tmp_conf = import_conf.copy()
        tmp_conf.pop('import')

        # check if there is conflicts
        for k in tmp_conf.keys():
            if k in config.keys():
                raise Exception('Unable to import config file %s, key %s conflicts' % (confpath, k))

        # merge imported conf with config
        config.update(tmp_conf)
    # replace import filelist by conflist
    config['import'] = conflist


def load(filename):
    with open(filename) as fp:
        config = yaml.load(fp, Loader=yaml.SafeLoader)
    dir = posixpath.split(filename)[0]
    import_config_files(config, dir)
    resolve_config_vars(config)

    return config
