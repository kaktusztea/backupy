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
    zcompression = zipfile.ZIP_DEFLATED
except ImportError:
    zcompression = zipfile.ZIP_STORED

__author__ = 'kaktusz'
__version__ = '0.8'

colorred = '\033[1;31m'
colorreset = '\033[0m'
coloryellow = '\033[0;33m'
debug = True
sep = os.path.sep


def strip_hash_string_end(line):
    return line.split("#")[0].rstrip()


def strip_dash_string_end(line):
    while line.endswith("/"):
        line = line[:-1]
    return line


def strip_dash_string_start(line):
    while line.startswith("/"):
        line = line[1:]
    return line


def strip_hash_on_dict_values(mydict):
    for idx, mylist in mydict.items():
        if isinstance(mylist, list):
            for lidx, elem in enumerate(mylist):
                mydict[idx][lidx] = strip_hash_string_end(elem)
        else:
            mydict[idx] = strip_hash_string_end(mylist)
    return mydict


def strip_enddash_on_list(endinglist):
    for idx, elem in enumerate(endinglist):
        while elem.endswith("/"):
            elem = elem[:-1]
        endinglist[idx] = elem
    return endinglist


def check_string_contains_spaces(line):
    if " " in line:
        return True
    else:
        return False


def add_dot_for_endings(endinglist):
    for idx, elem in enumerate(endinglist):
        if not elem.startswith(".") and elem != "~":
            endinglist[idx] = "." + elem
    return endinglist


def getsub_dir_path(root, entry):
    if not root.startswith("/") or not entry.startswith("/"):
        return False
    root = strip_dash_string_end(root)
    entry = strip_dash_string_end(entry)

    len_entry = len(str.split(entry, '/'))
    temp = root.split("/")[len_entry-1:]
    return os.path.join(*temp)


def create_config_file(config_file_path):
    # TODO: store config lines in a fix order
    # http://stackoverflow.com/questions/9001509/how-can-i-sort-a-dictionary-by-key
    filehandler = ""
    cfghandler = configparser.ConfigParser()
    cfghandler['GLOBAL_EXCLUDES'] = {'exclude_endings': '~, swp',
                                     'exclude_files': 'Thumbs.db, abcdefgh.txt',
                                     'exclude_dir_names': 'my_globaly_exclude_dir'}
    for i in range(1, 4):
        cfghandler['BACKUP'+str(i)] = {'name': 'Document backup' + str(i) + '           # comments are allowed',
                                       'enabled': 'no',
                                       'archive_name': 'document_backup' + str(i),
                                       'result_dir': '/home/joe/mybackups',
                                       'method': 'targz',
                                       'followsym': 'yes',
                                       'withpath': 'no',
                                       'include_dirs': '/home/joe/humour, /home/joe/novels',
                                       'exclude_dir_names': 'garbage, temp',
                                       'exclude_dir_fullpathes': '/home/joe/humour/saskabare, /home/joe/novels/bad_ones',
                                       'exclude_endings': '~, gif, jpg, bak',
                                       'exclude_files': 'abc.log, swp.db'}
    try:
        filehandler = open(config_file_path, "w")
        cfghandler.write(filehandler, space_around_delimiters=True)
    except OSError as err:
        printError("Cannot create config file: %s" % config_file_path)
        printError("Error: %s" % err.strerror)
        sys.exit(1)
    finally:
        filehandler.close()


def check_python_version():
    try:
        assert sys.version_info >= (3, 4)
    except AssertionError:
        printError("Minimum python version: 3.4")
        printError("Exiting")
        sys.exit(1)


def get_leaf_from_path(path):
    """ get filename only from path """
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def get_date():
    now = datetime.datetime.now()
    nowstr = '%04d-%02d-%02d' % (now.year, now.month, now.day)
    return nowstr


def get_time():
    now = datetime.datetime.now()
    nowstr = '[%02d:%02d:%02d]' % (now.hour, now.minute, now.second)
    return nowstr


def get_time_short():
    """ http://stackoverflow.com/a/1094933 """
    now = datetime.datetime.now()
    nowstr = '%02d%02d' % (now.hour, now.minute)
    return nowstr


def printLog(log):
    pp = get_time() + " " + str(log)
    print(pp)


def printError(log):
    printLog(colorred + log + colorreset)


def printDebug(log):
    if debug:
        printLog(coloryellow + log + colorreset)


def sizeof_fmt(num, suffix='B'):
    """ returns with human readable byte size format """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def get_dir_free_space(dirname):
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
        # self.oserrorcodes = [(k, v, os.strerror(k)) for k, v in os.errno.errorcode.items()]

    @staticmethod
    def help():
        print("backupy v" + __version__ + "\n\n"
              "Start methods\n"
              "   ./backupy.py                      # at first run, generates default backup set config file\n"
              "                                     # if exists, starts with default backup set config file (~/.local/backupy/default.cfg)\n"
              "   ./backupy.py /foo/mybackup.cfg    # starts with custom backup set config file\n"
              "   ./backupy.py --help               # this help\n\n"
              "Example for config file:\n"
              "   [GLOBAL_EXCLUDES]                    # you can change options' values, but don't modify section name and option names!\n"
              "   exclude_files = Thumbs.db, temp.txt  # list of globally excluded filenames\n"
              "   exclude_endings = ~, swp             # list of globally excluded file extension types\n"
              "   exclude_dir_names = trash, garbage   # list of excluded directory names without path\n\n"
              "   [BACKUP1]                            # Mandatory name pattern: BACKUP[0-9] (99 max) ; don't write anything after the number\n"
              "   name = My Document backup            # write entry name here\n"
              "   enabled = yes                        # is this backup active. {yes, no}\n"
              "   archive_name = document_backup       # archive file name without extension\n"
              "   result_dir = /home/joe/mybackups     # Where to create the archive file\n"
              "   method = targz                       # Compression method {tar, targz, zip}\n"
              "   followsym = yes                      # Should compressor follow symlinks\n"
              "   withpath = no                        # compress files with or without full path\n"
              "   include_dirs = /home/joe/humour, /home/joe/novels   # list of included directories\n"
              "   exclude_dir_names = garbage, temp    # list of excluded directory names without path\n"
              "   exclude_dir_fullpathes = /home/joe/humour/saskabare, /home/joe/novels/bad_ones  # list of excluded directories with full path\n"
              "   exclude_endings = ~, gif, jpg, bak   # list of excluded file extension types\n"
              "   exclude_files = abc.log, Thumbs.db   # list of excluded filenames\n\n"
              "Tip 1: use of comment sign '#' is allowed - at the end of option lines\n\n"
              "Tip 2: exclude_endings' special case: '~' -> it excludes file endings like 'myfile.doc~'  (NOT myfile.~) \n")

    @staticmethod
    def get_configs_global(config_file):
        bconfig = {}
        cfghandler = configparser.ConfigParser()
        try:
            cfghandler.read(config_file)
            bconfig['sections'] = cfghandler.sections()

            ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_endings', raw=False)
            bconfig['exclude_endings'] = list(map(str.strip, ll.split(',')))
            bconfig['exclude_endings'] = add_dot_for_endings(bconfig['exclude_endings'])

            ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_files', raw=False)
            bconfig['exclude_files'] = list(map(str.strip, ll.split(',')))

            ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_dir_names', raw=False)
            bconfig['exclude_dir_names'] = list(map(str.strip, ll.split(',')))
            bconfig['exclude_dir_names'] = strip_enddash_on_list(bconfig['exclude_dir_names'])

            bconfig = strip_hash_on_dict_values(bconfig)
        except configparser.Error as err:
            printError("Config file syntax error: %s" % config_file)
            printError("%s" % err.message)
            sys.exit(1)
        except OSError as oerr:
            printError("OSError: %s" % config_file)
            printError("%s (%s)" % (oerr.strerror, str(oerr.errno)))
            sys.exit(1)
        else:
            return bconfig

    def get_configs_userbackup(self, config_file):
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
                    bconfig['section'] = section
                    bconfig['enabled'] = cfghandler.get(section, 'enabled', raw=False)
                    bconfig['name'] = cfghandler.get(section, 'name', raw=False)
                    bconfig['archive_name'] = cfghandler.get(section, 'archive_name', raw=False)

                    bconfig['result_dir'] = cfghandler.get(section, 'result_dir', raw=False)
                    bconfig['method'] = cfghandler.get(section, 'method', raw=False)
                    bconfig['followsym'] = cfghandler.get(section, 'followsym', raw=False)
                    bconfig['withpath'] = cfghandler.get(section, 'withpath', raw=False)

                    ll = cfghandler.get(section, 'include_dirs', raw=False)
                    bconfig['include_dirs'] = list(map(str.strip, ll.split(',')))
                    bconfig['include_dirs'] = strip_enddash_on_list(bconfig['include_dirs'])

                    ll = cfghandler.get(section, 'exclude_dir_names', raw=False)
                    bconfig['exclude_dir_names'] = list(map(str.strip, ll.split(',')))
                    bconfig['exclude_dir_names'] = strip_enddash_on_list(bconfig['exclude_dir_names'])

                    ll = cfghandler.get(section, 'exclude_dir_fullpathes', raw=False)
                    bconfig['exclude_dir_fullpathes'] = list(map(str.strip, ll.split(',')))
                    bconfig['exclude_dir_fullpathes'] = strip_enddash_on_list(bconfig['exclude_dir_fullpathes'])

                    ll = cfghandler.get(section, 'exclude_endings', raw=False)
                    bconfig['exclude_endings'] = list(map(str.strip, ll.split(',')))
                    bconfig['exclude_endings'] = add_dot_for_endings(bconfig['exclude_endings'])

                    ll = cfghandler.get(section, 'exclude_files', raw=False)
                    bconfig['exclude_files'] = list(map(str.strip, ll.split(',')))

                    bconfig = strip_hash_on_dict_values(bconfig)
                    if check_string_contains_spaces(bconfig['archive_name']):
                        printError("Space in archive name is not allowed: %s" % bconfig['archive_name'])
                        printError("Exiting")
                        sys.exit(1)

                    bconfig['archivefullpath'] = 'replace_this'
                    if bconfig['method'] == 'tar':
                        bconfig['archive_name'] += '_' + get_date() + '_' + get_time_short() + '.tar'
                    elif bconfig['method'] == 'targz':
                        bconfig['archive_name'] += '_' + get_date() + '_' + get_time_short() + '.tar.gz'
                    elif bconfig['method'] == 'zip':
                        bconfig['archive_name'] += '_' + get_date() + '_' + get_time_short() + '.zip'
                    else:
                        printError("Error: wrong compression method declared in section %s" % section)
                        printError("Valid: method = { tar ; targz ; zip}")
                        printError("Exiting")
                        sys.exit(1)
                    self.check_mandatory_options(bconfig)
                    allconfigs[section] = bconfig
        except (configparser.NoSectionError, configparser.NoOptionError, configparser.Error) as err:
            printError("Invalid config file: %s" % config_file)
            printError("%s" % err.message)
            sys.exit(1)
        else:
            return allconfigs

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
            printLog("Don't forget to set 'enabled' to 'yes' if you want a backup entry to be active!")
            sys.exit(0)

    def check_mandatory_options(self, bckentry):
        mandatory = ['name', 'archive_name', 'method', 'followsym', 'result_dir', 'withpath', 'include_dirs']
        err = False
        for ops in mandatory:
            if isinstance(bckentry[ops], list):
                if len(bckentry[ops]) != 1:
                    continue
                if bckentry[ops][0].strip() == "":
                    err = True
            elif isinstance(bckentry[ops], str):
                if bckentry[ops].strip() == "":
                    err = True
            else:
                printError("BUG! This can not happen! def check_mandatory_options()")
                sys.exit(1)
            if err:
                # TODO: use print_config_error()
                printError("Invalid config file: %s" % self.path_config_file)
                printError("[%s]: '%s' option is mandatory!" % (bckentry['section'], ops))
                sys.exit(1)

    def filter_general(self, item):
        mode = ""
        filenamefull = ""
        if isinstance(item, str):
            filenamefull = item
            mode = "zip"
        elif isinstance(item, tarfile.TarInfo):
            filenamefull = item.name
            mode = "tar"

    # def filter_tar(self, tarinfo):
        """ filter function for tar creation - general and custom """
        # It works, only PEP8 shows warnings
        # http://stackoverflow.com/questions/23962434/pycharm-expected-type-integral-got-str-instead
    #     if tarinfo.name.endswith(tuple(self.configs_global['exclude_endings'])):
    #         return None
    #     elif tarinfo.name.endswith(tuple(self.configs_user[self.cfg_actual]['exclude_endings'])):
    #         return None
    #
    #     #  It works, only Pycharm-PEP8 shows warnings
    #     elif get_leaf_from_path(tarinfo.name) in self.configs_global['exclude_files']:
    #         return None
    #     elif get_leaf_from_path(tarinfo.name) in self.configs_user[self.cfg_actual]['exclude_files']:
    #         return None
    #
    #     #  It works, only Pycharm-PEP8 shows warnings
    #     if any(dirname in tarinfo.name.split("/") for dirname in self.configs_global['exclude_dir_names']):
    #         return None
    #     if any(dirname in tarinfo.name.split("/") for dirname in self.configs_user[self.cfg_actual]['exclude_dir_names']):
    #         return None
    #
    #     else:
    #         return tarinfo
    #
    # def filter_zip(self, filenamefull, bckentry):
        # fn = os.path.join(base, file)
        # zfile.write(fn, fn[rootlen:])
        if filenamefull.endswith(tuple(self.configs_global['exclude_endings'])):
            printDebug("Global exclude ending: %s" % filenamefull)  # DEBUG
            return None
        elif filenamefull.endswith(tuple(self.configs_user[self.cfg_actual]['exclude_endings'])):
            printDebug("User exclude ending: %s" % filenamefull)  # DEBUG
            return None

        #  It works, only Pycharm-PEP8 shows warnings
        elif get_leaf_from_path(filenamefull) in self.configs_global['exclude_files']:
            printDebug("Global exclude file: %s" % filenamefull)  # DEBUG
            return None
        elif get_leaf_from_path(filenamefull) in self.configs_user[self.cfg_actual]['exclude_files']:
            printDebug("User exclude file: %s" % filenamefull)  # DEBUG
            return None

        #  It works, only Pycharm-PEP8 shows warnings
        # TODO:only after the basedir!!
        if any(dirname in filenamefull.split("/") for dirname in self.configs_global['exclude_dir_names']):
            printDebug("Global exclude dir names matched at: %s" % filenamefull)  # DEBUG
            return None
        if any(dirname in filenamefull.split("/") for dirname in self.configs_user[self.cfg_actual]['exclude_dir_names']):
            printDebug("User exclude dir names matched at: %s" % filenamefull)    # DEBUG
            return None
        else:
            if mode == "zip":
                return True
            if mode == "tar":
                return item

    def compress_pre(self, path_target_dir, bckentry):
        """" Checks and prints backup entry processing """
        filepath = os.path.join(path_target_dir, bckentry['archive_name'])
        bckentry['archivefullpath'] = filepath

        if bckentry['enabled'].lower() != "yes":
            printLog("--------------------------------------------------")
            printLog("Backup entry \"%s\" is DISABLED --> SKIPPING" % bckentry['name'])
            return False
        if os.path.isfile(filepath):
            printLog("--------------------------------------------------")
            printLog("Executing backup '%s'" % bckentry['name'])
            printError("There is already an archive with this name: %s" % filepath)
            printError("Skipping")

            return False

        else:
            printLog("--------------------------------------------------")
            printLog("Executing backup task: \"%s\"" % bckentry['name'])
            if not os.path.isdir(path_target_dir):
                printError("Config file: %s" % self.path_config_file)
                printError("Section: [%s]" % bckentry['section'])
                printError("Target directory does not exists: %s" % path_target_dir)
                sys.exit(1)
            printLog("Creating archive: %s" % filepath)
            printLog("Compressing method: %s" % bckentry['method'])
            printLog("Free space in target dir: %s" % get_dir_free_space(path_target_dir))
        return True

    def compress_tar(self, bckentry):
        """ Compressing with tar/targz method """

        archive = ""
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

            # http://stackoverflow.com/a/39321142/4325232
            dereference = True if bckentry['followsym'] == "yes" else False
            archive = tarfile.open(name=filepath, mode=mode, dereference=dereference)

            if bckentry['withpath'] == 'yes':
                for entry in bckentry['include_dirs']:
                    archive.add(entry, filter=self.filter_general())
            elif bckentry['withpath'] == 'no':
                for entry in bckentry['include_dirs']:
                    archive.add(entry, arcname=os.path.basename(entry), filter=self.filter_general)
            else:
                printError("Wrong 'withpath' config value! Should be \"yes\" / \"no\". Exiting.")
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
        finally:
            archive.close()
        filesize = os.path.getsize(filepath)
        printLog("Done [%s]" % sizeof_fmt(filesize))

    def compress_zip(self, bckentry):
        """ Compressing with zip method """
        # TODO: need to add description?

        # TODO: Exclude def: only with full path in .cfg file!!

        archive = ""
        filepath = bckentry['archivefullpath']
        try:
            archive = zipfile.ZipFile(file=filepath, mode="w", compression=zcompression)
            # archive.comment = bckentry['description']
            for entry in bckentry['include_dirs']:
                for root, dirs, files in os.walk(top=entry, followlinks=True):
                    for filename in files:
                        dirpart = getsub_dir_path(root, entry)
                        if self.filter_general(os.path.join(root, filename)):    # TODO: None as return code is passing! BUG!
                            if bckentry['withpath'] == 'yes':
                                archive.write(filename=os.path.join(root, filename), compress_type=zcompression)
                            elif bckentry['withpath'] == 'no':
                                archive.write(filename=os.path.join(root, filename), arcname=os.path.join(dirpart, filename), compress_type=zcompression)
                            else:
                                printError("Wrong 'withpath' config value! Should be \"yes\" / \"no\". Exiting.")
                                sys.exit(1)

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
        finally:
            archive.close()
        filesize = os.path.getsize(filepath)
        printLog("Done [%s]" % sizeof_fmt(filesize))

    def read_configs(self):
        printLog("backupy v" + __version__ + " starting")
        self.check_first_run()

        # Create user backup config file list
        self.configs_global = self.get_configs_global(self.path_config_file)
        self.configs_user = self.get_configs_userbackup(self.path_config_file)

        if self.configs_user is False:
            printLog("---------------------------------------------------------------")
            printLog("You don't have any active user backup entries in %s" % self.path_config_file)
            printLog("Exiting.")
            sys.exit(1)

    def execute_backups(self):
        for cfname, bckentry in self.configs_user.items():
            self.cfg_actual = cfname
            mode = bckentry['method']

            # self.check_mandatory_options(bckentry)
            if self.compress_pre(bckentry['result_dir'], bckentry):
                print("%s Starting backup" % get_time())
                if mode == "tar" or mode == "targz":
                    self.compress_tar(bckentry)
                elif mode == "zip":
                    self.compress_zip(bckentry)
                else:
                    printLog("Wrong method type. Exiting.")
                    sys.exit(1)
        printLog("--------------------------------------------------")
        printLog("backupy finished")


def main():
    check_python_version()
    backupy = Backupy()
    backupy.read_configs()
    backupy.execute_backups()


if __name__ == '__main__':
    # sys.exit(main(sys.argv[1]))
    sys.exit(main())
