#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import sys
import os


def getBackupConfigs(configfile):
    if not os.path.exists(configfile):
        print("Config file does not exists.")
        sys.exit(1)

    bconfig = {}
    conffile = configparser.ConfigParser()
    try:
        conffile.read(configfile)
        bconfig['sections'] = conffile.sections()
        bconfig['name'] = conffile.get('backupentry', 'NAME', raw=False)
        bconfig['filename'] = conffile.get('backupentry', 'FILENAME', raw=False)
        bconfig['resultpath'] = conffile.get('backupentry', 'RESULTPATH', raw=False)
        bconfig['method'] = conffile.get('backupentry', 'METHOD', raw=False)
        bconfig['followsym'] = conffile.get('backupentry', 'FOLLOWSYM', raw=False)
        bconfig['withoutpath'] = conffile.get('backupentry', 'WITHOUTPATH', raw=False)

        ll = conffile.get('backupentry', 'INCLUDE_DIR', raw=False)
        bconfig['include_dir'] = ll.split(',')

        ll = conffile.get('backupentry', 'EXCLUDE_DIRS', raw=False)
        bconfig['exclude_dirs'] = ll.split(',')

        ll = conffile.get('backupentry', 'EXCLUDE_ENDINGS', raw=False)
        bconfig['exclude_endings'] = ll.split(',')

        ll = conffile.get('backupentry', 'EXCLUDE_FILES', raw=False)
        bconfig['exclude_files'] = ll.split(',')
    except (configparser.NoSectionError, configparser.NoOptionError) as err:
        print("Error in config file: %s" % configfile)
        print("Error: %s" % err.message)

    return bconfig


def getGlobalConfigs(globalconfig):
    if not os.path.exists(globalconfig):
        print("Global config file does not exists.")
        sys.exit(1)
    bconfig = {}
    conffile = configparser.ConfigParser()
    try:
        conffile.read(globalconfig)
        bconfig['sections'] = conffile.sections()

        ll = conffile.get('BACKUPY_GLOBALS', 'EXCLUDE_ENDINGS', raw=False)
        bconfig['exclude_endings'] = ll.split(',')

        ll = conffile.get('BACKUPY_GLOBALS', 'EXCLUDE_FILES', raw=False)
        bconfig['exclude_files'] = ll.split(',')

        ll = conffile.get('BACKUPY_GLOBALS', 'EXCLUDE_DIRS', raw=False)
        bconfig['exclude_dirs'] = ll.split(',')
    except configparser.NoSectionError as err:
        print("Global config file syntax error: %s" % globalconfig)
        print("Error: %s" % err.message)
    return bconfig
