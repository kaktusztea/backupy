#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import sys
import errno
import ntpath
import tarfile
import zipfile
import datetime
import configparser
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except ImportError:
    compression = zipfile.ZIP_STORED

__author__ = 'kaktusz'


def stripHashAtEnd(line):
    return line.split("#")[0].rstrip()


def stripHashInDictValues(mydict):
    for idx, mylist in mydict.items():
        if isinstance(mylist, list):
            for lidx, elem in enumerate(mylist):
                mydict[idx][lidx] = stripHashAtEnd(elem)
        # elif mylist is str:
        else:
            mydict[idx] = stripHashAtEnd(mylist)
    return mydict


def checkIfContainsSpaces(line):
    if " " in line:
        return True
    else:
        return False


def stripDashAtEnd(endinglist):
    for idx, elem in enumerate(endinglist):
        while elem.endswith("/"):
            elem = elem[:-1]
        endinglist[idx] = elem
    return endinglist


def dotForEndings(endinglist):
    for idx, elem in enumerate(endinglist):
        if not elem.startswith("."):
            endinglist[idx] = "." + elem
    return endinglist


def create_config_file(config_file_path):
    filehandler = ""
    cfghandler = configparser.ConfigParser()
    cfghandler['GLOBAL_EXCLUDES'] = {'EXCLUDE_ENDINGS': '~, swp',
                                     'EXCLUDE_FILES': 'Thumbs.db, abcdefgh.txt',
                                     'EXCLUDE_DIRS': 'my_globaly_exclude_dir'}
    for i in range(1, 4):
        cfghandler['BACKUP'+str(i)] = {'NAME': 'Document backup' + str(i),
                                       'ENABLED': 'FALSE',
                                       'ARCHIVE_NAME': 'document_backup' + str(i),
                                       'RESULT_DIR': '/home/joe/mybackups',
                                       'METHOD': 'targz',
                                       'FOLLOWSYM': 'yes',
                                       'WITHPATH': 'no',
                                       'INCLUDE_DIRS': '/home/joe/humour, /home/joe/novels',
                                       'EXCLUDE_DIRS': 'garbage, temp',
                                       'EXCLUDE_ENDINGS': '~, gif, jpg, bak',
                                       'EXCLUDE_FILES': 'abc.log, Thumbs.db'}
    try:
        filehandler = open(config_file_path, "w")
        cfghandler.write(filehandler, space_around_delimiters=True)
    except OSError as err:
        printLog("Cannot create config file: %s" % config_file_path)
        printLog("Error: %s" % err.strerror)
        sys.exit(1)
    finally:
        filehandler.close()


def getBackupConfigs(configfile):
    if not os.path.exists(configfile):
        print("Config file does not exists.")
        sys.exit(1)

    allconfigs = {}
    conffile = configparser.ConfigParser()
    try:
        conffile.read(configfile)
        section_list = conffile.sections()
        pattern = re.compile("BACKUP[0-9]{1,2}$")
        for section in section_list:
            if pattern.match(section):
                bconfig = {}
                bconfig['enabled'] = conffile.get(section, 'enabled', raw=False)
                bconfig['name'] = conffile.get(section, 'name', raw=False)
                bconfig['archive_name'] = conffile.get(section, 'archive_name', raw=False)

                bconfig['result_dir'] = conffile.get(section, 'result_dir', raw=False)
                bconfig['method'] = conffile.get(section, 'method', raw=False)
                bconfig['followsym'] = conffile.get(section, 'followsym', raw=False)
                bconfig['withpath'] = conffile.get(section, 'withpath', raw=False)

                ll = conffile.get(section, 'include_dirs', raw=False)
                bconfig['include_dirs'] = list(map(str.strip, ll.split(',')))
                bconfig['include_dirs'] = stripDashAtEnd(bconfig['include_dirs'])

                ll = conffile.get(section, 'exclude_dirs', raw=False)
                bconfig['exclude_dirs'] = list(map(str.strip, ll.split(',')))
                bconfig['exclude_dirs'] = stripDashAtEnd(bconfig['exclude_dirs'])

                ll = conffile.get(section, 'exclude_endings', raw=False)
                bconfig['exclude_endings'] = list(map(str.strip, ll.split(',')))
                bconfig['exclude_endings'] = dotForEndings(bconfig['exclude_endings'])

                ll = conffile.get(section, 'exclude_files', raw=False)
                bconfig['exclude_files'] = list(map(str.strip, ll.split(',')))

                bconfig = stripHashInDictValues(bconfig)
                if checkIfContainsSpaces(bconfig['archive_name']):
                    raise configparser.Error("Space in archive name is not allowed.")

                bconfig['archivefullpath'] = 'replace_this'
                if bconfig['method'] == 'tar':
                    bconfig['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.tar'
                elif bconfig['method'] == 'targz':
                    bconfig['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.tar.gz'
                elif bconfig['method'] == 'zip':
                    bconfig['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.zip'
                else:
                    printLog("Error: wrong compression method declared in section %s" % section)
                    printLog("Valid: method = { tar ; targz ; zip}")
                    printLog("Exiting")
                    sys.exit(1)
                allconfigs[section] = bconfig

    except (configparser.NoSectionError, configparser.NoOptionError, configparser.Error) as err:
        print("Invalid config file: %s" % configfile)
        print("Error: %s" % err.message)
        sys.exit(1)
    else:
        return allconfigs


def getGlobalConfigs(config_file):
    bconfig = {}
    cfghandler = configparser.ConfigParser()
    try:
        cfghandler.read(config_file)
        bconfig['sections'] = cfghandler.sections()

        ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_endings', raw=False)
        bconfig['exclude_endings'] = list(map(str.strip, ll.split(',')))
        bconfig['exclude_endings'] = dotForEndings(bconfig['exclude_endings'])

        ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_files', raw=False)
        bconfig['exclude_files'] = list(map(str.strip, ll.split(',')))

        ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_dirs', raw=False)
        bconfig['exclude_dirs'] = list(map(str.strip, ll.split(',')))
        bconfig['exclude_dirs'] = stripDashAtEnd(bconfig['exclude_dirs'])

        bconfig = stripHashInDictValues(bconfig)

    except configparser.NoSectionError as err:
        printLog("Global config file syntax error: %s" % config_file)
        printLog("Error: %s" % err.message)
        sys.exit(1)
    else:
        return bconfig


def checkPythonVersion():
    try:
        assert sys.version_info >= (3, 4)
    except AssertionError:
        printLog("Minimum python version: 3.4")
        printLog("Exiting")
        sys.exit(1)


def path_leaf(path):
    """ get filename only from path """
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def getDate():
    now = datetime.datetime.now()
    nowstr = '%04d-%02d-%02d' % (now.year, now.month, now.day)
    return nowstr


def getTime():
    now = datetime.datetime.now()
    nowstr = '[%02d:%02d:%02d]' % (now.hour, now.minute, now.second)
    return nowstr


def getTimeShort():
    """ http://stackoverflow.com/a/1094933 """
    now = datetime.datetime.now()
    nowstr = '%02d%02d' % (now.hour, now.minute)
    return nowstr


def printLog(log):
    pp = getTime() + " " + str(log)
    print(pp)


def sizeof_fmt(num, suffix='B'):
    """ returns with human readable byte size format """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def getFreeSpace(dirname):
    """ returns directory's free space in human readable format """
    st = os.statvfs(dirname)
    return sizeof_fmt(st.f_bavail * st.f_frsize)


class Backupy:
    """ Backupy class """
    def __init__(self):
        self.home_path = os.path.expanduser("~")
        self.path_configdir = self.home_path + '/.config/backupy'
        self.path_config_file = self.path_configdir + '/backupy.cfg'
        # self.path_config_global = self.path_configdir + '/globals.cfg'
        self.path_config_entry_list = []

        self.configs_global = ""
        self.configs_user = {}
        self.cfg_actual = ''

        self.oserrorcodes = [(k, v, os.strerror(k)) for k, v in os.errno.errorcode.items()]

    @staticmethod
    def help():
        print("[BACKUP1]                            # Mandatory name pattern: BACKUP[0-9]  ; don't write anything after the number\n"
              "NAME = Document backup               # write entry name here\n"
              "ENABLED = TRUE                       # is this backup active. {TRUE, FALSE}\n"
              "ARCHIVE_NAME = document_backup       # archive file name without extension\n"
              "RESULT_DIR = /home/joe/mybackups     # Where to create the archive file\n"
              "METHOD = targz                       # Compression method {tar, targz, zip}\n"
              "FOLLOWSYM = yes                      # Should compressor follow symlinks\n"
              "WITHPATH = no                       # compress files with or without full path\n"
              "INCLUDE_DIRS = /home/joe/humour, /home/joe/novels   # list of included directories\n"
              "EXCLUDE_DIRS = garbage, temp         # list of excluded directories\n"
              "EXCLUDE_ENDINGS = ~, gif, jpg, bak   # excluded file extension types\n"
              "EXCLUDE_FILES = abc.log, Thumbs.db   # excluded filenames")

    def firstRun(self):
        if not os.path.exists(self.home_path):
            printLog("Can not access home directory: %s" % self.home_path)
            sys.exit(1)

        if not os.path.exists(self.path_configdir):
            try:
                os.mkdir(self.path_configdir)
            except OSError as err:
                printLog("Cannot create user config dir: %s" % self.path_configdir)
                printLog("Error: %s" % err.strerror)
                sys.exit(1)

        if not os.path.exists(self.path_config_file):
            printLog("First run!")
            printLog("Generating config file: %s" % self.path_config_file)
            create_config_file(self.path_config_file)
            printLog("---------------------------------------------------------------")
            printLog("Now you can create user specified backup entries in %s" % self.path_config_file)
            printLog("Don't forget to set 'ENABLED' to 'True' if you want a backup entry to be active!")
            sys.exit(0)

    # @staticmethod
    # def getConfigList(dirname):
    #     """ Filters config file list: only user configs """
    #     blacklist = ['globals.cfg', '.sample']
    #     files = [os.path.join(dirname, f) for f in os.listdir(dirname)
    #              if os.path.isfile(os.path.join(dirname, f))
    #              and not any(f.endswith(ext) for ext in blacklist)]
    #     return files

    def filter_tar(self, tarinfo):
        """ filter function for tar creation - general and custom """
        # It works, only PEP8 shows warnings
        # http://stackoverflow.com/questions/23962434/pycharm-expected-type-integral-got-str-instead
        if tarinfo.name.endswith(tuple(self.configs_global['exclude_endings'])):
            return None
        elif tarinfo.name.endswith(tuple(self.configs_user[self.cfg_actual]['exclude_endings'])):
            return None

        #  It works, only PEP8 shows warnings
        elif path_leaf(tarinfo.name) in self.configs_global['exclude_files']:
            return None
        elif path_leaf(tarinfo.name) in self.configs_user[self.cfg_actual]['exclude_files']:
            return None

        #  It works, only PEP8 shows warnings
        # TODO: WITHPATH==FALSE -> works;  WITHPATH==TRUE -> doesn't work
        elif path_leaf(tarinfo.name) in self.configs_global['exclude_dirs']:
            return None
        elif path_leaf(tarinfo.name) in self.configs_user[self.cfg_actual]['exclude_dirs']:
            return None
        else:
            return tarinfo

    @staticmethod
    def compress_pre(path_target_dir, bckentry):
        """" Checks and prints backup entry processing """
        filepath = os.path.join(path_target_dir, bckentry['archive_name'])
        bckentry['archivefullpath'] = filepath

        if bckentry['enabled'].lower() != "true":
            printLog("--------------------------------------------------")
            printLog("Backup entry \"%s\" is DISABLED --> SKIPPING" % bckentry['name'])
            return False
        if os.path.isfile(filepath):
            printLog("--------------------------------------------------")
            printLog("Executing backup '%s'" % bckentry['name'])
            printLog("There is already an archive with this name: %s" % filepath)
            printLog("Skipping")
            return False
        else:
            printLog("--------------------------------------------------")
            printLog("Executing backup task: \"%s\"" % bckentry['name'])
            printLog("Creating archive: %s" % filepath)
            printLog("Compressing method: %s" % bckentry['method'])
            printLog("Free space in target dir: %s" % getFreeSpace(path_target_dir))
        return True

    def compress_tar(self, bckentry):
        """ Compressing with tar/targz method """
        filepath = bckentry['archivefullpath']
        try:
            mode = ""
            if bckentry['method'] == "tar":
                mode = "w"
            elif bckentry['method'] == "targz":
                mode = "w:gz"
            else:
                printLog("Error: wrong tar compress method (%s)." % bckentry['method'])
                printLog("Exiting")
                sys.exit(1)

            # TODO: Implement "follow symlinks" option!
            archive = tarfile.open(filepath, mode)
            if bckentry['withpath'] == 'yes':
                for entry in bckentry['include_dirs']:
                    archive.add(entry, filter=self.filter_tar)
            elif bckentry['withpath'] == 'no':
                for entry in bckentry['include_dirs']:
                    archive.add(entry, arcname=os.path.basename(entry), filter=self.filter_tar)
            else:
                printLog("Wrong 'withpath' config value! Should be \"YES\" / \"NO\". Exiting.")
                sys.exit(1)
        except (IOError, OSError) as err:
            if err.errno == errno.EACCES:
                # printLog("OSError: Permission denied on %s" % filepath)
                printLog("OSError: %s on %s" % (os.strerror(err.errno), filepath))
                sys.exit(err.errno)
            if err.errno == errno.ENOSPC:
                printLog("OSError: No space on disk")
                sys.exit(err.errno)
            if err.errno == errno.ENOENT:
                printLog("IOError/OSError: No such file or directory to compress: %s" % filepath)
                sys.exit(err.errno)
            else:
                printLog("IOError/OSError: Unhandled error: %s" % err.strerror)
                sys.exit(99)
        else:
            archive.close()
            filesize = os.path.getsize(filepath)
            printLog("Done [%s]" % sizeof_fmt(filesize))

    def compress_zip(self, t, bobject):           # TODO: full obsolete, rewrite, refactor!
        """ Compressing with zip method """
        dirpath = bobject['pathcompress'] + "/*"
        filepath = os.path.join(t['path'], bobject['archive_name'])

        try:
            archive = zipfile.ZipFile(filepath, mode="w")                   # TODO: filtering!
            archive.comment = bobject['description']
            archive.write(dirpath, compress_type=compression)
        except (IOError, OSError) as err:
            if err.errno == errno.EACCES:
                printLog("IOError/OSError: Can't write to this file: %s" % filepath)
                sys.exit(err.errno)
            if err.errno == errno.ENOSPC:
                printLog("IOError/OSError: No space on disk")
                sys.exit(err.errno)
            if err.errno == errno.ENOENT:
                printLog("IOError/OSError: No such file or directory to compress: %s" % filepath)
                sys.exit(err.errno)
            else:
                printLog("IOError/OSError: Unhandled error: %s" % err.strerror)
                sys.exit(99)
        else:
            archive.close()
            filesize = os.path.getsize(filepath)
            printLog("Done [%s]" % sizeof_fmt(filesize))

    def read_configs(self):
        printLog("backupy starting")
        self.firstRun()

        # Create user backup config file list
        self.configs_global = getGlobalConfigs(self.path_config_file)
        self.configs_user = getBackupConfigs(self.path_config_file)

        if self.configs_user is False:
            printLog("---------------------------------------------------------------")
            printLog("You don't have any active user backup entries in %s" % self.path_config_file)
            printLog("Exiting.")
            sys.exit(1)

    def execute_backups(self):
        for cfname, cfentry in self.configs_user.items():
            self.cfg_actual = cfname
            mode = cfentry['method']

            if self.compress_pre(cfentry['result_dir'], cfentry):
                print("%s Starting backup" % getTime())
                if mode == "tar" or mode == "targz":
                    self.compress_tar(cfentry)
                # elif mode == "zip":
                #     compress_zip(target, backupentry)
                else:
                    printLog("Wrong method type. Exiting.")
                    sys.exit(1)
        printLog("--------------------------------------------------")
        printLog("backupy finished")


def main():
    checkPythonVersion()
    backupy = Backupy()
    backupy.read_configs()
    backupy.execute_backups()


if __name__ == '__main__':
    # sys.exit(main(sys.argv[1]))
    sys.exit(main())
