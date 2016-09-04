#!/usr/bin/env python3
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
__version__ = '0.8'

colorred = '\033[1;31m'
colorreset = '\033[0m'


def stripHashAtEnd(line):
    return line.split("#")[0].rstrip()


def stripHashInDictValues(mydict):
    for idx, mylist in mydict.items():
        if isinstance(mylist, list):
            for lidx, elem in enumerate(mylist):
                mydict[idx][lidx] = stripHashAtEnd(elem)
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
    # TODO: store config lines in a fix order
    # http://stackoverflow.com/questions/9001509/how-can-i-sort-a-dictionary-by-key
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
        printError("Cannot create config file: %s" % config_file_path)
        printError("Error: %s" % err.strerror)
        sys.exit(1)
    finally:
        filehandler.close()


def get_configs_userbackup(config_file):
    if not os.path.exists(config_file):
        printError("Config file does not exists: %s" % config_file)
        sys.exit(1)

    allconfigs = {}
    cfghandler = configparser.ConfigParser()
    try:
        cfghandler.read(config_file)
        section_list = cfghandler.sections()
        pattern = re.compile("BACKUP[0-9]{1,2}$")
        for section in section_list:
            if pattern.match(section):
                bconfig = {}
                bconfig['enabled'] = cfghandler.get(section, 'enabled', raw=False)
                bconfig['name'] = cfghandler.get(section, 'name', raw=False)
                bconfig['archive_name'] = cfghandler.get(section, 'archive_name', raw=False)

                bconfig['result_dir'] = cfghandler.get(section, 'result_dir', raw=False)
                bconfig['method'] = cfghandler.get(section, 'method', raw=False)
                bconfig['followsym'] = cfghandler.get(section, 'followsym', raw=False)
                bconfig['withpath'] = cfghandler.get(section, 'withpath', raw=False)

                ll = cfghandler.get(section, 'include_dirs', raw=False)
                bconfig['include_dirs'] = list(map(str.strip, ll.split(',')))
                bconfig['include_dirs'] = stripDashAtEnd(bconfig['include_dirs'])

                ll = cfghandler.get(section, 'exclude_dirs', raw=False)
                bconfig['exclude_dirs'] = list(map(str.strip, ll.split(',')))
                bconfig['exclude_dirs'] = stripDashAtEnd(bconfig['exclude_dirs'])

                ll = cfghandler.get(section, 'exclude_endings', raw=False)
                bconfig['exclude_endings'] = list(map(str.strip, ll.split(',')))
                bconfig['exclude_endings'] = dotForEndings(bconfig['exclude_endings'])

                ll = cfghandler.get(section, 'exclude_files', raw=False)
                bconfig['exclude_files'] = list(map(str.strip, ll.split(',')))

                bconfig = stripHashInDictValues(bconfig)
                if checkIfContainsSpaces(bconfig['archive_name']):
                    printError("Space in archive name is not allowed: %s" % bconfig['archive_name'])
                    printError("Exiting")
                    sys.exit(1)

                bconfig['archivefullpath'] = 'replace_this'
                if bconfig['method'] == 'tar':
                    bconfig['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.tar'
                elif bconfig['method'] == 'targz':
                    bconfig['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.tar.gz'
                elif bconfig['method'] == 'zip':
                    bconfig['archive_name'] += '_' + getDate() + '_' + getTimeShort() + '.zip'
                else:
                    printError("Error: wrong compression method declared in section %s" % section)
                    printError("Valid: method = { tar ; targz ; zip}")
                    printError("Exiting")
                    sys.exit(1)
                allconfigs[section] = bconfig

    except (configparser.NoSectionError, configparser.NoOptionError, configparser.Error) as err:
        printError("Invalid config file: %s" % config_file)
        printError("%s" % err.message)
        sys.exit(1)
    else:
        return allconfigs


def get_configs_global(config_file):
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
    except configparser.Error as err:
        printError("Config file syntax error: %s" % config_file)
        printError("%s" % err.message)
        sys.exit(1)
    except OSError as oerr:
        printError("OSError: %s" % config_file)
        printError("%s (%s)" % (oerr.message, str(oerr.errno)))
        sys.exit(1)
    else:
        return bconfig


def checkPythonVersion():
    try:
        assert sys.version_info >= (3, 4)
    except AssertionError:
        printError("Minimum python version: 3.4")
        printError("Exiting")
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


def printError(log):
    printLog(colorred + log + colorreset)


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
        self.path_default_configdir = self.home_path + '/.config/backupy'
        self.path_default_config_file = self.path_default_configdir + '/default.cfg'
        if len(sys.argv) == 2:
            if sys.argv[1] == "--help":
                self.help()
                sys.exit(0)
            if not os.path.exists(sys.argv[1]):
                printLog("Config file does not exists: %s" % sys.argv[1])
                sys.exit(1)
            else:
                self.path_configdir = os.path.dirname(os.path.abspath(sys.argv[1]))
                self.path_config_file = os.path.abspath(sys.argv[1])
        elif len(sys.argv) > 2:
            self.help()
            sys.exit(1)
        else:
            self.path_configdir = self.path_default_configdir
            self.path_config_file = self.path_default_config_file

        self.configs_global = ""
        self.configs_user = {}
        self.cfg_actual = ''

        self.oserrorcodes = [(k, v, os.strerror(k)) for k, v in os.errno.errorcode.items()]

    @staticmethod
    def help():
        print("backupy v" + __version__ + "\n\n"
              "Start methods\n"
              "   ./backupy.py                      # at first run, generates default backup set config file\n"
              "                                     # if exists, starts with default backup set config file (~/.local/backupy/default.cfg)\n"
              "   ./backupy.py /foo/mybackup.cfg    # starts with custom backup set config file\n"
              "   ./backupy.py --help               # this help\n\n"
              "Example for config file:\n"
              "[GLOBAL_EXCLUDES]                    # you can change options' values, but don't modify section name and option names!\n"
              "\n"
              "[BACKUP1]                            # Mandatory name pattern: BACKUP[0-9] (99 max) ; don't write anything after the number\n"
              "name = My Document backup            # write entry name here\n"
              "enabled = true                       # is this backup active. {true, false}\n"
              "archive_name = document_backup       # archive file name without extension\n"
              "result_dir = /home/joe/mybackups     # Where to create the archive file\n"
              "method = targz                       # Compression method {tar, targz, zip}\n"
              "followsym = yes                      # Should compressor follow symlinks\n"
              "withpath = no                        # compress files with or without full path\n"
              "include_dirs = /home/joe/humour, /home/joe/novels   # list of included directories\n"
              "exclude_dirs = garbage, temp         # list of excluded directories\n"
              "exclude_endings = ~, gif, jpg, bak   # excluded file extension types\n"
              "exclude_files = abc.log, Thumbs.db   # excluded filenames")

    def check_first_run(self):
        if not os.path.exists(self.home_path):
            printError("Can not access home directory: %s" % self.home_path)
            sys.exit(1)

        if not os.path.exists(self.path_default_configdir):
            try:
                os.mkdir(self.path_default_configdir)
            except OSError as err:
                printError("Cannot create user config dir: %s" % self.path_default_configdir)
                printError("%s" % err.strerror)
                sys.exit(1)

        if not os.path.exists(self.path_default_config_file):
            printLog("First run!")
            printLog("Generating default config file: %s" % self.path_default_config_file)
            create_config_file(self.path_default_config_file)
            printLog("---------------------------------------------------------------")
            printLog("Now you can create user specified backup entries in %s" % self.path_default_config_file)
            printLog("Also you can create custom user specified backup set config file(s) - called as command line parameter.")
            printLog("Don't forget to set 'ENABLED' to 'True' if you want a backup entry to be active!")
            sys.exit(0)

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
                printError("Error: wrong tar compress method (%s)." % bckentry['method'])
                printError("Exiting")
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
                printError("Wrong 'withpath' config value! Should be \"YES\" / \"NO\". Exiting.")
                sys.exit(1)
        except (IOError, OSError) as err:
            # TODO: it is not necessary handle every type of exception. Just write 'errno' and 'strerror'
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

    def compress_zip(self, bckentry):
        """ Compressing with zip method """
        # TODO: this is obsolete -> rewrite, refactor!
        # http://stackoverflow.com/a/14569017

        dirpath = bckentry['pathcompress'] + "/*"
        filepath = bckentry['archivefullpath']
        try:
            archive = zipfile.ZipFile(filepath, mode="w")                   # TODO: filtering!
            archive.comment = bckentry['description']
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
        self.check_first_run()

        # Create user backup config file list
        self.configs_global = get_configs_global(self.path_config_file)
        self.configs_user = get_configs_userbackup(self.path_config_file)

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
                elif mode == "zip":
                    self.compress_zip(cfentry)
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
