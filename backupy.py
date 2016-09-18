#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    backupy: a handly tool for selectively backup your data

    Features:
    * backup sets separatable in unique files (passed as command line parameter)
    * unique backup entries in backup sets (up to 99)
    * global exclude lists (file, dir, filetype) for entire backup set
    * every backup entry is customizable
        * enabled / disabled
        * archive file name
        * compression method (tar, targz, tarbz2, zip)
        * store files/directories with/without full path
        * follow symlinks (yes/no)
        * include directories
        * exclude directory names
        * exclude directory with fullpath
        * exclude filenames
        * exclude filetypes (special: '~' ==> mynovel.doc~ )
        * result dir
"""

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

# Globals
__author__ = 'Balint Fekete'
__copyright__ = 'Copyright 2016, Balint Fekete'
__license__ = 'GPLv3'
__version__ = '1.0.2'
__maintainer__ = 'Balint Fekete'
__email__ = 'kaktusztea at_ protonmail dot_ ch'
__status__ = 'Production'

debug = False
colorred = '\033[1;31m'
colorreset = '\033[0m'
coloryellow = '\033[0;93m'
colorblue = '\033[1;2;34m'


def strip_hash_string_end(line):
    if isinstance(line, str):
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


def check_string_contains_comma(line):
    if "," in line:
        return True
    else:
        return False


def check_if_symlink_broken(path):
    if os.path.islink(path) and not os.path.exists(path):
        return True
    else:
        return False


def add_dot_for_endings(endinglist):
    for idx, elem in enumerate(endinglist):
        if not elem.startswith(".") and elem != "~":
            endinglist[idx] = "." + elem
    return endinglist


def getsub_dir_path(root, longpath):
    if not root.startswith("/") or not longpath.startswith("/"):
        return False
    root = strip_dash_string_end(root)
    longpath = strip_dash_string_end(longpath)

    len_root = len(str.split(root, '/'))
    temp = longpath.split("/")[len_root - 1:]
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
                                       'include_dir1': '/home/joe/humour                # at least one is mandatory',
                                       'include_dir2': '/home/joe/novels',
                                       'exclude_dir_names': 'garbage, temp',
                                       'exclude_dir_fullpath': '/home/joe/humour/saskabare, /home/joe/novels/bad_ones',
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


def printWarning(log):
    if isinstance(log, str):
        printLog(coloryellow + log + colorreset)
    if isinstance(log, list):
        for line in log:
            printLog(coloryellow + line + colorreset)


def printError(log):
    printLog(colorred + log + colorreset)


def printDebug(log):
    if debug:
        printLog(coloryellow + log + colorreset)


def exit_config_error(config_file, section, comment, exitnow=True):
    printError("%s" % config_file)
    printError("[%s]" % section)
    if isinstance(comment, str):
        printError(comment)
    if isinstance(comment, list):
        for line in comment:
            printError(line)
    if exitnow:
        sys.exit(1)


def print_config_warning(config_file, section, comment):
    printWarning("%s" % config_file)
    printWarning("[%s]" % section)
    if isinstance(comment, str):
        printWarning(comment)
    if isinstance(comment, list):
        for line in comment:
            printWarning(line)


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

    def help(self):
        print("backupy v" + __version__ + "\n\n"
              "Start methods\n"
              "   ./backupy.py                      # at first run, generates default backup set config file\n"
              "                                     # if exists, starts with default backup set config file (~/.local/backupy/default.cfg)\n"
              "   ./backupy.py /foo/mybackup.cfg    # starts with custom backup set config file\n"
              "   ./backupy.py --help               # this help\n\n"
              "Example for config file\n"
              "   [GLOBAL_EXCLUDES]                    # you can change options' values, but don't modify section name and option names!\n"
              "   exclude_files = Thumbs.db, temp.txt  # list of globally excluded filenames\n"
              "   exclude_endings = ~, swp             # list of globally excluded file extension types\n"
              "   exclude_dir_names = trash, garbage   # list of globally excluded directory names without path\n\n"
              "   [BACKUP1]                            # Mandatory name pattern: BACKUP[0-9] (99 max) ; don't write anything after the number\n"
              "  *name = My Document backup            # write entry name here\n"
              "  *enabled = yes                        # is this backup active. {yes, no}\n"
              "  *archive_name = document_backup       # archive file name without extension\n"
              "  *result_dir = /home/joe/mybackups     # Where to create the archive file\n"
              "  *method = targz                       # Compression method {tar, targz, tarbz2, zip}\n"
              "  *followsym = yes                      # Should compressor follow symlinks\n"
              "  *withpath = no                        # compress files with or without full path\n"
              "  *include_dir1 = /home/joe/humour      # included directory 1. (at least one is mandatory)\n"
              "   include_dir2 = /home/joe/novels      # included directory 2.\n"
              "   inlcude_dirN = ... \n"
              "   ... \n"
              "   exclude_dir_names = garbage, temp    # list of excluded directory names without path\n"
              "   exclude_dir_fullpath1 = /home/joe/humour/saskabare   # exclude directory 1. Not mandatory.\n"
              "   exclude_dir_fullpath2 = /home/joe/novels/bad_ones\n"
              "   exclude_dir_fullpathN = ...\n"
              "   ...\n"
              "   exclude_endings = ~, gif, jpg, bak   # list of excluded file extension types\n"
              "   exclude_files = abc.log, Thumbs.db   # list of excluded filenames\n\n"
              "   * Mandatory options\n\n"
              "Tip 1: use of comment sign '#' is allowed - at the end of option lines\n"
              "Tip 2: 'exclude_endings' special case: '~'  It excludes file endings like 'myfile.doc~'  (NOT myfile.~) \n"
              "Tip 3: 'exclude_dir_names' are active only _below_ the included directory's root path\n")
        if not os.path.exists(self.path_default_config_file):
            printWarning("\nYou did not run backupy init yet.")
            printWarning("Just run ./backupy.py and let it create default config for you.\n")

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
        cfghandler = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        cfghandler.optionxform = str
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

                    i = 1
                    bconfig['include_dir'] = []
                    while 'include_dir'+str(i) in cfghandler[section]:
                        ll = cfghandler.get(section, 'include_dir'+str(i), raw=False)
                        if len(ll) > 0:
                            bconfig['include_dir'].append(ll)
                        i += 1
                    bconfig['include_dir'] = strip_enddash_on_list(bconfig['include_dir'])

                    i = 1
                    bconfig['exclude_dir_fullpath'] = []
                    while 'exclude_dir_fullpath'+str(i) in cfghandler[section]:
                        ll = cfghandler.get(section, 'exclude_dir_fullpath'+str(i), raw=False)
                        if len(ll) > 0:
                            bconfig['exclude_dir_fullpath'].append(ll)
                        i += 1
                    bconfig['exclude_dir_fullpath'] = strip_enddash_on_list(bconfig['exclude_dir_fullpath'])

                    # exclude_dir_names
                    ll = cfghandler.get(section, 'exclude_dir_names', raw=False)
                    bconfig['exclude_dir_names'] = list(map(str.strip, ll.split(',')))
                    bconfig['exclude_dir_names'] = strip_enddash_on_list(bconfig['exclude_dir_names'])

                    # exclude_endings
                    ll = cfghandler.get(section, 'exclude_endings', raw=False)
                    bconfig['exclude_endings'] = list(map(str.strip, ll.split(',')))
                    bconfig['exclude_endings'] = add_dot_for_endings(bconfig['exclude_endings'])

                    # exclude_files
                    ll = cfghandler.get(section, 'exclude_files', raw=False)
                    bconfig['exclude_files'] = list(map(str.strip, ll.split(',')))

                    # strip # (comment) at the line endings
                    bconfig = strip_hash_on_dict_values(bconfig)

                    # archive_name
                    if check_string_contains_spaces(bconfig['archive_name']):
                        comment = "Space in archive name is not allowed: %s" % bconfig['archive_name']
                        exit_config_error(config_file, section, comment)
                    if bconfig['archive_name'].strip() == '':
                        errmsg = "'archive_name' is mandatory."
                        exit_config_error(config_file, section, errmsg)

                    # include_dir
                    for n, inclpath in enumerate(bconfig['include_dir']):
                        if check_string_contains_spaces(inclpath) or check_string_contains_comma(inclpath):
                            errmsg = "Space, comma in 'include_dir"+str(n+1)+" is not allowed"
                            exit_config_error(config_file, section, errmsg)

                    # exclude_dir_fullpath
                    for n, exclpath in enumerate(bconfig['exclude_dir_fullpath']):
                        if check_string_contains_spaces(exclpath) or check_string_contains_comma(exclpath):
                            errmsg = "Space, comma in 'exclude_dir%s' is not allowed" % str(n+1)
                            exit_config_error(config_file, section, errmsg)

                    bconfig['archivefullpath'] = 'replace_this'

                    if bconfig['method'] == 'tar':
                        bconfig['archive_name'] += '_' + get_date() + '_' + get_time_short() + '.tar'
                    elif bconfig['method'] == 'targz':
                        bconfig['archive_name'] += '_' + get_date() + '_' + get_time_short() + '.tar.gz'
                    elif bconfig['method'] == 'tarbz2':
                        bconfig['archive_name'] += '_' + get_date() + '_' + get_time_short() + '.tar.bz2'
                    elif bconfig['method'] == 'zip':
                        bconfig['archive_name'] += '_' + get_date() + '_' + get_time_short() + '.zip'
                    else:
                        comment = ["Wrong compression method declared (%s)" % bconfig['method'],
                                   "method = { tar ; targz ; tarbz2; zip}"]
                        exit_config_error(config_file, section, comment)

                    self.check_mandatory_options(bconfig)
                    if not self.check_include_dir_dups(bconfig):
                        exit_config_error(config_file, section, "'include_dirN' duplicates are not allowed.")

                    allconfigs[section] = bconfig
            if not self.check_archivename_unique(allconfigs):
                exit_config_error(config_file, "General error", "'archive_name'+'result_dir' combo should be unique between enabled backup entries!")

        except (configparser.NoSectionError, configparser.NoOptionError, configparser.Error) as err:
            printError("Invalid config file: %s" % config_file)
            printError("%s" % err.message)
            sys.exit(1)
        else:
            printLog("Config file is valid: %s" % config_file)
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
            printLog("Also you can create custom user specified backup-set config file(s) - called as command line parameter.")
            printLog("Don't forget to set 'enabled' to 'yes' if you want a backup entry to be active!\n")
            printWarning("backupy.py --help is your friend.\n")
            sys.exit(0)

    def check_mandatory_options(self, bckentry):
        mandatory = ['enabled', 'name', 'archive_name', 'method', 'followsym', 'result_dir', 'withpath', 'include_dir']
        yes_no_ops = ['enabled', 'followsym', 'withpath']
        err = False
        for ops in mandatory:
            if isinstance(bckentry[ops], list):
                if len(bckentry[ops]) > 1:
                    continue
                if len(bckentry[ops]) == 0:
                    err = True
                elif bckentry[ops][0].strip() == "":
                    err = True
            elif isinstance(bckentry[ops], str):
                if bckentry[ops].strip() == "":
                    err = True
            else:
                printError("BUG! This can not happen! def check_mandatory_options()")
                sys.exit(1)
            if err:
                comment = "'%s' is mandatory!" % ops
                exit_config_error(self.path_config_file, bckentry['section'], comment)
        for opss in yes_no_ops:
            if bckentry[opss] not in ['yes', 'no']:
                comment = "'%s' = {yes, no}" % opss
                exit_config_error(self.path_config_file, bckentry['section'], comment)

    @staticmethod
    def check_archivename_unique(allconfigs):
        ll = {bentry['section']: [bentry['archive_name'], bentry['result_dir']] for section, bentry in allconfigs.items() if bentry['enabled'] == 'yes'}
        for section, elem in ll.items():
            for section2, elem2 in ll.items():
                if section != section2 and elem[0] == elem2[0] and elem[1] == elem2[1]:
                    return False
        return True

    @staticmethod
    def check_include_dir_dups(bconfig):
        return len(bconfig['include_dir']) == len(set(bconfig['include_dir']))

    def filter_general(self, item, root_dir=''):
        mode = ""
        retval_skip = ""
        filenamefull = ""
        if isinstance(item, str):
            filenamefull = item
            mode = "zip"
            retval_skip = False
        elif isinstance(item, tarfile.TarInfo):
            filenamefull = os.path.join(root_dir, item.name)
            mode = "tar"
            retval_skip = None

        # if check_if_symlink_broken(filenamefull):
        #     printWarning("broken symlink (skip): %s" % filenamefull)
        #     return retval_skip

        # exclude_endings; only Pycharm-PEP8 warning
        if filenamefull.endswith(tuple(self.configs_global['exclude_endings'])):
            printDebug("Global exclude ending: %s" % filenamefull)
            return retval_skip
        elif filenamefull.endswith(tuple(self.configs_user[self.cfg_actual]['exclude_endings'])):
            printDebug("User exclude ending: %s" % filenamefull)
            return retval_skip

        #  exclude_files; only Pycharm-PEP8 warning
        elif get_leaf_from_path(filenamefull) in self.configs_global['exclude_files']:
            printDebug("Global exclude file: %s" % filenamefull)
            return retval_skip
        elif get_leaf_from_path(filenamefull) in self.configs_user[self.cfg_actual]['exclude_files']:
            printDebug("User exclude file: %s" % filenamefull)
            return retval_skip

        # exclude_dir_names; only Pycharm-PEP8 warning
        ll = getsub_dir_path(root_dir, filenamefull)
        if any(dirname in ll.split("/") for dirname in self.configs_global['exclude_dir_names']):
            printDebug("Global exclude dir names matched at: %s" % filenamefull)
            return retval_skip
        if any(dirname in ll.split("/")[1:] for dirname in self.configs_user[self.cfg_actual]['exclude_dir_names']):
            printDebug("User exclude dir names matched at: %s" % filenamefull)
            return retval_skip

        # exclude_dir_fullpath (only user exclude); only Pycharm-PEP8 warning
        if any(dirname in filenamefull for dirname in self.configs_user[self.cfg_actual]['exclude_dir_fullpath']):
            printDebug("User exclude dir with fullpath matched at: %s" % filenamefull)
            return retval_skip

        # No filtering occured, file can be passed to compressor
        if mode == "zip":
            return True
        elif mode == "tar":
            return item
        else:
            printError("filter_general(): Impossible return value.\n")
            raise Exception("filter_general(): Impossible return value.")

    def compress_pre(self, path_target_dir, bckentry):
        """" Checks and prints backup entry processing """
        filepath = os.path.join(path_target_dir, bckentry['archive_name'])
        bckentry['archivefullpath'] = filepath

        printLog("--------------------------------------------------")
        if bckentry['enabled'].lower() != "yes":
            printLog("Backup entry \"%s\" is DISABLED --> SKIPPING" % bckentry['name'])
            return False
        printLog("Executing backup task: \"" + colorblue + bckentry['name'] + colorreset + "\"")
        if os.path.isfile(filepath):
            printWarning("There is already an archive with this name:")
            printWarning("%s" % filepath)
            printWarning("Skipping")
            return False
        else:
            if not os.path.isdir(path_target_dir):
                comment = "Result directory does not exists: %s" % path_target_dir
                exit_config_error(self.path_config_file, bckentry['section'], comment)
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
            elif bckentry['method'] == "tarbz2":
                mode = "w:bz2"
            else:
                comment = ["Wrong compression method declared (%s)" % bckentry['method'],
                           "method = { tar ; targz ; tarbz2; zip}"]
                exit_config_error(self.path_config_file, bckentry['section'], comment)

            # http://stackoverflow.com/a/39321142/4325232
            dereference = True if bckentry['followsym'] == "yes" else False
            archive = tarfile.open(name=filepath, mode=mode, dereference=dereference)

            if bckentry['withpath'] == 'yes':
                for entry in bckentry['include_dir']:
                    archive.add(entry, filter=lambda x: self.filter_general(x, os.path.dirname(entry)))
            elif bckentry['withpath'] == 'no':
                for entry in bckentry['include_dir']:
                    # http://stackoverflow.com/questions/39438335/python-how-could-i-access-tarfile-adds-name-parameter-in-adds-filter-me
                    archive.add(entry, arcname=os.path.basename(entry), filter=lambda x: self.filter_general(x, os.path.dirname(entry)))
            else:
                printError("Wrong 'withpath' config value! Should be \"yes\" / \"no\". Exiting.")
                sys.exit(1)
        except (IOError, OSError) as err:
            if err.errno == errno.EACCES:
                printError("OSError: %s on %s" % (os.strerror(err.errno), filepath))
                sys.exit(err.errno)
            if err.errno == errno.ENOSPC:
                printError("OSError: No space on disk")
                sys.exit(err.errno)
            if err.errno == errno.ENOENT:
                # TODO / http://stackoverflow.com/questions/39545741/python-tarfile-add-how-to-avoid-exception-in-case-of-follow-symlink-broken
                printError("OSError: broken symlink or can not find file")
                sys.exit(err.errno)
            else:
                printError("IOError/OSError: Unhandled exception: %s" % err.strerror)
                sys.exit(99)
        finally:
            archive.close()
        filesize = os.path.getsize(filepath)
        printLog("Done [%s]" % sizeof_fmt(filesize))

    def compress_zip(self, bckentry):
        """ Compressing with zip method """
        archive = ""
        filepath = bckentry['archivefullpath']
        try:
            archive = zipfile.ZipFile(file=filepath, mode="w", compression=zcompression)
            # archive.comment = bckentry['description']            # TODO: need to add description?
        except (IOError, OSError) as err:
            if archive:
                archive.close()
            if err.errno == errno.EACCES:
                printError("OSError: Can't write to this file: %s" % filepath)
                sys.exit(err.errno)
            elif err.errno == errno.ENOSPC:
                printError("IOError/OSError: No space on disk")
                sys.exit(err.errno)
            else:
                printError("IOError/OSError: Unhandled error: %s" % err.strerror)
                sys.exit(99)

        # filtering + adding procedure starts by walking through on every file path
        for entry in bckentry['include_dir']:
            for subdir, dirs, files in os.walk(top=entry, followlinks=True):
                for filename in files:
                    dirpart = getsub_dir_path(entry, subdir)
                    if self.filter_general(os.path.join(subdir, filename), entry):
                        file_fullpath = os.path.join(subdir, filename)

                        if check_if_symlink_broken(file_fullpath):
                            printWarning("broken symlink (skip): %s" % file_fullpath)
                            continue

                        try:
                            if bckentry['withpath'] == 'yes':
                                archive.write(filename=file_fullpath, compress_type=zcompression)
                            elif bckentry['withpath'] == 'no':
                                archive.write(filename=file_fullpath, arcname=os.path.join(dirpart, filename), compress_type=zcompression)
                            else:
                                printError("Wrong 'withpath' config value! Should be \"yes\" / \"no\". Exiting.")
                                sys.exit(1)
                        except (UnicodeEncodeError, IOError, OSError, PermissionError) as err:
                            if isinstance(err, UnicodeEncodeError):
                                printWarning("Skip file (name encoding problem in dir): " + subdir)
                                continue
                            if isinstance(err, PermissionError):
                                try:
                                    printWarning("Skip file (permission error): %s " % file_fullpath)
                                except UnicodeEncodeError:
                                    printWarning("Skip file (permission AND name encoding problem somewhere in dir): " + subdir)
                                continue
                            elif err.errno == errno.ENOENT:
                                printLog("OSError: No such file or directory to compress: %s" % filepath)
                                continue
                            else:
                                printLog("Unhandled IOError/OSError: %s" % err.strerror)
                                continue
        if archive:
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

            if self.compress_pre(bckentry['result_dir'], bckentry):
                print("%s Starting backup" % get_time())
                if mode == "tar" or mode == "targz" or mode == "tarbz2":
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
