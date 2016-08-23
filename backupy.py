#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'kaktusz'
import os
import sys
import errno
import ntpath
import tarfile
import datetime
import zipfile
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

import ConfigHandler


def checkPythonVersion():
    try:
        assert sys.version_info >= (3, 4)
    except AssertionError as err:
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
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def getFreeSpace(dirname):
    st = os.statvfs(dirname)
    return sizeof_fmt(st.f_bavail * st.f_frsize)


class Backupy:
    """ Backupy class """
    def __init__(self):
        self.home_path = os.path.expanduser("~")
        self.path_configdir = self.home_path + '/.config/backupy'
        self.path_config_global = self.path_configdir + '/globals.cfg'
        self.path_config_entry_list = []

        self.config_global = ""
        self.configs_user = {}
        self.cfg_actual = ''

        self.oserrorcodes = [(k, v, os.strerror(k)) for k, v in os.errno.errorcode.items()]

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

        if not os.path.exists(self.path_config_global):
            samplecfgfile = self.path_configdir + "/mybackup.cfg.sample"
            printLog("First run!")
            printLog("Generating global configs: %s" % self.path_config_global)
            try:
                fhg = open(self.path_config_global, "w")
                fhg.write("[BACKUPY_GLOBALS]\n\
EXCLUDE_ENDINGS = .bak, .swp\n\
EXCLUDE_FILES = Thumbs.db, faja.txt\n\
EXCLUDE_DIRS = myexcldirg_global\n")
                fhg.close()
                del fhg
            except OSError as err:
                printLog("Cannot create global config: %s" % self.path_config_global)
                printLog("Error: %s" % err.strerror)
                sys.exit(1)

            printLog("Generating sample backup config: %s" % samplecfgfile)
            try:
                fhg = open(samplecfgfile, "w")
                fhg.write("[backupentry]\n\
NAME = Document backup\n\
ENABLED = TRUE\n\
ARCHIVE_NAME = document_backup\n\
RESULT_DIR = /home/friedrich/mybackups\n\
METHOD = targz\n\
FOLLOWSYM = yes\n\
WITHOUTPATH = yes\n\
INCLUDE_DIRS = /home/friedrich/documents/memoirs, /home/fiedrich/documents/novels\n\
EXCLUDE_DIRS = garbage, temp\n\
EXCLUDE_ENDINGS = ~, gif, jpg, bak\n\
EXCLUDE_FILES = abc.log, Thumbs.db\n")
                fhg.close()
            except OSError as err:
                printLog("Cannot create sample backup config: %s" % self.path_config_global)
                printLog("Error: %s" % err.strerror)
                sys.exit(1)

            printLog("---------------------------------------------------------------")
            printLog("Now you can create user specified backup entries in %s" % self.path_configdir)
            printLog("Copy sample file above as many times as you want and customize!")
            printLog("Important: User backup config files' extension should be .cfg")
            sys.exit(0)

    def getConfigList(self, dirname):
        """ Filters config file list: only user configs """
        blacklist = ['globals.cfg', '.sample']
        files = [os.path.join(dirname, f) for f in os.listdir(dirname)
                 if os.path.isfile(os.path.join(dirname, f))
                 and not any(f.endswith(ext) for ext in blacklist)]
        return files

    def filter_general(self, tarinfo):
        """ filter function for tar creation - general and custom """
        # TODO: It works, but PEP8 shows warnings
        # http://stackoverflow.com/questions/23962434/pycharm-expected-type-integral-got-str-instead
        if tarinfo.name.endswith(tuple(self.config_global['exclude_endings'])):
            return None
        elif tarinfo.name.endswith(tuple(self.configs_user[self.cfg_actual]['exclude_endings'])):
            return None

        # TODO: It works, but PEP8 shows warnings
        elif path_leaf(tarinfo.name) in self.config_global['exclude_files']:
            return None
        elif path_leaf(tarinfo.name) in self.configs_user[self.cfg_actual]['exclude_files']:
            return None

        # TODO: It works, but PEP8 shows warnings
        elif path_leaf(tarinfo.name) in self.config_global['exclude_dirs']:
            return None
        elif path_leaf(tarinfo.name) in self.configs_user[self.cfg_actual]['exclude_dirs']:
            return None
        else:
            return tarinfo

    def compress_pre(self, path_target_dir, bckentry):
        """" Checks and prints backup entry processing """
        filepath = os.path.join(path_target_dir, bckentry['archive_name'])
        bckentry['archivefullpath'] = filepath

        if bckentry['enabled'].lower() != "true":
            printLog("Backup entry \"%s\" is DISABLED, SKIPPING." % bckentry['name'])
            return False
        if os.path.isfile(filepath):
            printLog("There is already an archive with this name: %s" % filepath)
            printLog("Skipping")
            return False
        else:
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

            archive = tarfile.open(filepath, mode)
            if bckentry['withoutpath'] == 'no':
                for entry in bckentry['include_dirs']:
                    archive.add(entry, filter=self.filter_general)
            elif bckentry['withoutpath'] == 'yes':
                for entry in bckentry['include_dirs']:
                    archive.add(entry, arcname=os.path.basename(entry), filter=self.filter_general)
            else:
                printLog("Wrong 'filepath' value!")
                printLog("Exiting")
                sys.exit(1)        # TODO: only skipping!
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

    def init(self):
        printLog("backupy starting")
        self.firstRun()

        # Create user backup config file list
        self.config_global = ConfigHandler.getGlobalConfigs(self.path_config_global)
        self.path_config_entry_list = self.getConfigList(self.path_configdir)
        if not self.path_config_entry_list:
            printLog("---------------------------------------------------------------")
            printLog("You don't have any user backup config in %s" % self.path_configdir)
            printLog("Copy sample file there - as many times as you want - and customize!")
            printLog("Important: User backup config files' extension should be .cfg")
            sys.exit(1)

        # Read user backup config files in iteration
        for cfpath in self.path_config_entry_list:
            leaf = path_leaf(cfpath)
            self.configs_user[leaf] = ConfigHandler.getBackupConfigs(cfpath)
            self.configs_user[leaf]['archivefullpath'] = 'replace_this'
            if self.configs_user[leaf]['method'] == 'tar':
                self.configs_user[leaf]['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.tar'
            if self.configs_user[leaf]['method'] == 'targz':
                self.configs_user[leaf]['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.tar.gz'
            if self.configs_user[leaf]['method'] == 'zip':
                self.configs_user[leaf]['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.zip'

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


def main():
    checkPythonVersion()
    backupy = Backupy()
    backupy.init()
    backupy.execute_backups()


if __name__ == '__main__':
    # sys.exit(main(sys.argv[1]))
    sys.exit(main())
