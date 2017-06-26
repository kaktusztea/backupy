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
import csv
import errno
import shutil
import ntpath
import random
import string
import hashlib
import tarfile
import zipfile
import datetime
import platform
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
__version__ = '1.1.2'
__maintainer__ = 'Balint Fekete'
__email__ = 'kaktusztea at_ protonmail dot_ ch'
__status__ = 'Production'

debug = True
colorred = '\033[1;31m'
colorreset = '\033[0m'
coloryellow = '\033[0;93m'
colorblue = '\033[1;2;34m'
colorgreen = "\033[1;32m"


def strip_dash_string_end(line):
    while line.endswith("/"):
        line = line[:-1]
    return line


def strip_dash_string_start(line):
    while line.startswith("/"):
        line = line[1:]
    return line


def strip_hash_string_end(line):
    if isinstance(line, str):
        return line.split("#")[0].rstrip()
    else:
        raise Exception("Error in def: strip_hash_string_end()")


def strip_hash_on_list_values(mylist):
    if isinstance(mylist, list):
        for idx, elem in enumerate(mylist):
            if isinstance(elem, list):     # recursive call
                mylist[idx] = strip_hash_on_list_values(elem)
            elif isinstance(elem, str):
                mylist[idx] = strip_hash_string_end(elem)
            else:
                raise Exception("Error in def: strip_hash_on_list_values()")
    return mylist


def strip_hash_on_dict_values(mydict):
    for idx, mylist in mydict.items():
        if isinstance(mylist, list):
            strip_hash_on_list_values(mylist)
            # for lidx, elem in enumerate(mylist):
            #     mydict[idx][lidx] = strip_hash_string_end(elem)
        elif isinstance(mylist, str):
            mydict[idx] = strip_hash_string_end(mylist)
        else:
            raise Exception("Error in def: strip_hash_on_dict_values()")
    return mydict


def strip_hash(element):
    if isinstance(element, dict):
        return strip_hash_on_dict_values(element)
    if isinstance(element, list):
        return strip_hash_on_list_values(element)
    if isinstance(element, str):
        return strip_hash_string_end(element)


def strip_enddash_on_list(endinglist):
    for idx, elem in enumerate(endinglist):
        while elem.endswith("/"):
            elem = elem[:-1]
        endinglist[idx] = elem
    return endinglist


def convert_to_bool(mystr):
    if str(mystr).lower() == 'yes':
        return True
    elif str(mystr).lower() == 'no':
        return False
    return -1


def check_string_contains_spaces(line):
    return " " in line


def check_string_contains_comma(line):
    return "," in line


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


def filter_nonexistent_include_dirs(include_dirs):
    remove_indexes = []
    for index, dirpath in enumerate(include_dirs):
        if not os.path.exists(dirpath):
            remove_indexes.append(index)
            printWarning("Include dir doesn't exist, skipping: %s" % str(dirpath))
    remove_indexes.sort(reverse=True)
    if remove_indexes:
        for index in remove_indexes:
            del include_dirs[index]
        return True    # there was at least one unaccessable dir


def check_if_file_is_unreadable(path):
    return not os.access(path, os.R_OK)


def get_unreadable_files_in_recursive_subdir(subdir, followsym):
    lista = []
    for root, dirs, files in os.walk(subdir):
        for file in files:
            ffile = os.path.join(root, file)
            if followsym:
                if check_if_file_is_unreadable(ffile):
                    lista.append(os.path.join(root, file))
            else:
                if check_if_file_is_unreadable(ffile) and not os.path.islink(ffile):
                    lista.append(os.path.join(root, file))
    return lista


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


def get_random_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def printLog(log):
    pp = get_time() + " " + str(log)
    print(pp)


def printWarning(log):
    if isinstance(log, str):
        printLog(coloryellow + log + colorreset)
    if isinstance(log, list):
        for line in log:
            printLog(" " + coloryellow + line + colorreset)


def printError(log):
    printLog(colorred + str(log) + colorreset)


def printDebug(log):
    if debug:
        printLog(coloryellow + str(log) + colorreset)


def printOK(log):
    printLog(colorgreen + str(log) + colorreset)


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


class Configglobal:
    def __init__(self):
        self.exclude_files = []
        self.exclude_endings = []
        self.exclude_dir_names = []


class Backupset:
    def __init__(self, config_file):
        if not os.path.exists(config_file):
            printError("Config file does not exists: %s" % config_file)
            sys.exit(1)
        self.config_file = config_file
        self.task_list = []
        self.g = Configglobal()
        # get configs
        self.get_configs_global()
        self.get_configs_task()

    def __del__(self):
        pass

    def check_archivename_unique(self):
        ll = [task for task in self.task_list if task.enabled]
        for task in ll:
            for task2 in ll:
                if task.section != task2.section and ((task.archive_name == task2.archive_name and task.path_result_dir == task2.path_result_dir) or task.name == task2.name):
                    return False
        return True

    def has_active_backuptask(self):
        for task in self.task_list:
            if task.enabled:
                return True
        return False

    def get_configs_global(self):
        cfghandler = configparser.ConfigParser()
        try:
            cfghandler.read(self.config_file)
            # self.section_list = cfghandler.sections()

            ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_endings', raw=False)
            self.g.exclude_endings = list(map(str.strip, ll.split(',')))
            self.g.exclude_endings = add_dot_for_endings(self.g.exclude_endings)

            ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_files', raw=False)
            self.g.exclude_files = list(map(str.strip, ll.split(',')))

            ll = cfghandler.get('GLOBAL_EXCLUDES', 'exclude_dir_names', raw=False)
            self.g.exclude_dir_names = list(map(str.strip, ll.split(',')))
            self.g.exclude_dir_names = strip_enddash_on_list(self.g.exclude_dir_names)
            self.g.exclude_dir_names = strip_hash_on_list_values(self.g.exclude_dir_names)

            # bconfig = strip_hash_on_dict_values(bconfig)
        except configparser.Error as err:
            printError("Config file syntax error: %s" % self.config_file)
            printError("%s" % err.message)
            sys.exit(1)
        except OSError as oerr:
            printError("OSError: %s" % self.config_file)
            printError("%s (%s)" % (oerr.strerror, str(oerr.errno)))
            sys.exit(1)

    def get_configs_task(self):
        cfghandler = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        cfghandler.optionxform = str
        try:
            cfghandler.read(self.config_file)
            pattern = re.compile("BACKUP[0-9]{1,2}$")
            for section in cfghandler.sections():
                if pattern.match(section):
                    task = Backuptask(section, self.g, self.config_file)
                    task.section = strip_hash(section)
                    task.enabled = convert_to_bool(strip_hash(cfghandler.get(section, 'enabled', raw=False)))

                    task.name = strip_hash(cfghandler.get(section, 'name', raw=False))
                    task.archive_name = strip_hash(cfghandler.get(section, 'archive_name', raw=False))

                    task.path_result_dir = strip_hash(cfghandler.get(section, 'result_dir', raw=False))
                    task.method = strip_hash(cfghandler.get(section, 'method', raw=False))
                    task.followsym = convert_to_bool(strip_hash(cfghandler.get(section, 'followsym', raw=False)))
                    task.withpath = convert_to_bool(strip_hash(cfghandler.get(section, 'withpath', raw=False)))
                    task.skip_if_permission_fail = convert_to_bool(strip_hash(cfghandler.get(section, 'skip_if_permission_fail', raw=False)))
                    task.skip_if_directory_nonexistent = convert_to_bool(strip_hash(cfghandler.get(section, 'skip_if_directory_nonexistent', raw=False)))

                    i = 1
                    while 'include_dir'+str(i) in cfghandler[section]:
                        ll = strip_hash(cfghandler.get(section, 'include_dir'+str(i), raw=False))
                        if len(ll) > 0:
                            task.include_dirs.append(ll)
                        i += 1
                    task.include_dirs = strip_enddash_on_list(task.include_dirs)

                    i = 1
                    while 'exclude_dir_fullpath'+str(i) in cfghandler[section]:
                        ll = strip_hash(cfghandler.get(section, 'exclude_dir_fullpath'+str(i), raw=False))
                        if len(ll) > 0:
                            task.exclude_dir_fullpath.append(ll)
                        i += 1
                    task.exclude_dir_fullpath = strip_enddash_on_list(task.exclude_dir_fullpath)

                    # exclude_dir_names
                    ll = strip_hash(cfghandler.get(section, 'exclude_dir_names', raw=False))
                    task.exclude_dir_names = list(map(str.strip, ll.split(',')))
                    task.exclude_dir_names = strip_enddash_on_list(task.exclude_dir_names)

                    # exclude_endings
                    ll = strip_hash(cfghandler.get(section, 'exclude_endings', raw=False))
                    task.exclude_endings = list(map(str.strip, ll.split(',')))
                    task.exclude_endings = add_dot_for_endings(task.exclude_endings)

                    # exclude_files
                    ll = strip_hash(cfghandler.get(section, 'exclude_files', raw=False))
                    task.exclude_files = list(map(str.strip, ll.split(',')))

                    # archive_name
                    if check_string_contains_spaces(task.archive_name):
                        comment = "Space in archive name is not allowed: %s" % task.archive_name
                        exit_config_error(self.config_file, section, comment)
                    if task.archive_name.strip() == '':
                        errmsg = "'archive_name' is mandatory."
                        exit_config_error(self.config_file, section, errmsg)

                    # include_dir
                    for n, inclpath in enumerate(task.include_dirs):
                        if check_string_contains_spaces(inclpath) or check_string_contains_comma(inclpath):
                            errmsg = "Space, comma in 'include_dir"+str(n+1)+" is not allowed"
                            exit_config_error(self.config_file, section, errmsg)

                    # exclude_dir_fullpath
                    for n, exclpath in enumerate(task.exclude_dir_fullpath):
                        if check_string_contains_spaces(exclpath) or check_string_contains_comma(exclpath):
                            errmsg = "Space, comma in 'exclude_dir%s' is not allowed" % str(n+1)
                            exit_config_error(self.config_file, section, errmsg)

                    if task.method == 'tar':
                        task.archive_name += '_' + get_date() + '_' + get_time_short() + '.tar'
                    elif task.method == 'targz':
                        task.archive_name += '_' + get_date() + '_' + get_time_short() + '.tar.gz'
                    elif task.method == 'tarbz2':
                        task.archive_name += '_' + get_date() + '_' + get_time_short() + '.tar.bz2'
                    elif task.method == 'zip':
                        task.archive_name += '_' + get_date() + '_' + get_time_short() + '.zip'
                    else:
                        comment = ["Wrong compression method declared (%s)" % task.method,
                                   "method = { tar ; targz ; tarbz2; zip}"]
                        exit_config_error(self.config_file, section, comment)

                    task.archivefullpath = os.path.join(task.path_result_dir, task.archive_name)

                    # checks
                    task.check_mandatory_options()
                    if not task.check_include_dir_dups():
                        exit_config_error(self.config_file, section, "'include_dirN' duplicates are not allowed.")

                    self.task_list.append(task)
                    del task

            if not self.check_archivename_unique():
                exit_config_error(self.config_file, "General error", "'result_dir' + 'archive_name' + 'method' combo and 'name' should be unique between enabled backup entries!")

        except (configparser.NoSectionError, configparser.NoOptionError, configparser.Error) as err:
            printError("Invalid config file: %s" % self.config_file)
            printError("%s" % err.message)
            sys.exit(1)
        else:
            printLog("Config file is valid: %s" % self.config_file)

    def execute(self):
        if not self.has_active_backuptask():
            printLog("---------------------------------------------------------------")
            printLog("You don't have any active backup task entries in %s" % self.config_file)
            printLog("Exiting.")
            return False
        for task in self.task_list:
            if task.enabled and task.compress_pre():
                if task.method == "tar" or task.method == "targz" or task.method == "tarbz2":
                    task.compress_tar()
                elif task.method == "zip":
                    task.compress_zip()
                else:
                    printLog("Wrong method type in %s." % task.name)


class Backuptask:
    def __init__(self, section, cglobal, path_config_file):
        self.section = section
        self.configs_global = {}
        self.archivefullpath = ''
        self.enabled = False
        self.name = ''
        self.archive_name = ''
        self.path_result_dir = ''
        self.method = ''
        self.followsym = False
        self.withpath = False
        self.skip_if_permission_fail = False
        self.skip_if_directory_nonexistent = False
        self.include_dirs = []
        self.exclude_dir_fullpath = []
        self.exclude_dir_names = []
        self.exclude_endings = []
        self.exclude_files = []
        self.configs_global = cglobal

        self.path_config_file = path_config_file
        self.path_stash = os.path.join(self.get_temp_dir(), str(os.getpid()))
        self.broken_syms = {}
        self.path_md5 = {}

    def __del__(self):
        if os.path.exists(self.path_stash):
            printLog("Cleaning up")
            shutil.rmtree(self.path_stash)

    def get_temp_dir(self):
        if self.get_os() == "Linux":
            return "/tmp/"
        elif self.get_os() == "Darwin":
            return "/tmp/"
        elif self.get_os() == "Windows":
            return "C:/Temp/"

    @staticmethod
    def get_os():
        return platform.system()

    def check_mandatory(self, option):
        err = False
        if isinstance(option, list):
            if len(option) == 0 or option[0].strip() == "":
                err = True
        elif str(self.enabled).strip() == "":
                err = True
        if err:
            raise Exception("'%s' is mandatory!" % option)

    def check_yes_no(self, option, name):
        if option == "-1":
            raise Exception("%s should be: {yes, no} (%s)" % (name, self.name))

    def check_mandatory_options(self):
        try:
            self.check_mandatory(self.enabled)
            self.check_mandatory(self.name)
            self.check_mandatory(self.archive_name)
            self.check_mandatory(self.method)
            self.check_mandatory(self.followsym)
            self.check_mandatory(self.path_result_dir)
            self.check_mandatory(self.withpath)
            self.check_mandatory(self.skip_if_permission_fail)
            self.check_mandatory(self.skip_if_directory_nonexistent)
            self.check_mandatory(self.include_dirs)
            self.check_mandatory(self.path_result_dir)
            self.check_yes_no(self.enabled, "enabled")
            self.check_yes_no(self.followsym, "followsym")
            self.check_yes_no(self.withpath, "withpath")
            self.check_yes_no(self.skip_if_permission_fail, "skip_if_permission_fail")
            self.check_yes_no(self.skip_if_directory_nonexistent, "skip_if_directory_nonexistent")
        except Exception as err:
            exit_config_error(self.path_config_file, self.section, err, exitnow=True)  # TODO: err  is OK?

    def check_include_dir_dups(self):
        return len(self.include_dirs) == len(set(self.include_dirs))

    @staticmethod
    def check_if_symlink_broken(path):
        return os.path.islink(path) and not os.path.exists(path)

    def get_broken_syms_in_recursive_subdir(self, subdir):
        broken_list = []
        for root, dirs, files in os.walk(subdir):
            for file in files:
                if self.check_if_symlink_broken(os.path.join(root, file)):
                    broken_list.append(os.path.join(root, file))
        if broken_list:
            if not os.path.exists(self.path_stash):
                try:
                    os.makedirs(name=self.path_stash, exist_ok=True)
                except OSError as err:
                    printError("Cannot create stash temp dir for broken symlinks: %s" % self.path_stash)
                    printError("(%s)" % err.strerror)
                    sys.exit(1)
            return broken_list
        return False

    def stash_broken_symlinks(self, entry, syms):
        if syms and isinstance(syms, list):
            printDebug("Stashing broken symlinks to %s for %s" % (self.path_stash, entry))
            for sym in syms:
                temp_target = os.path.join(self.path_stash, get_leaf_from_path(sym)) + '_' + get_random_string(7)
                self.broken_syms[sym] = temp_target
                try:
                    shutil.move(sym, temp_target)
                    # TODO: place a dummy file instead of broken symlink: BROKEN_SYMLINK_mybroken.txt
                    # TODO: Delete it at pop phase
                except OSError as err:
                    printError("Could not stash broken symlink: " + sym)
                    printError("(%s)" % err.strerror)
            printDebug("Broken symlinks and their stash location pairs:")
            printDebug(self.broken_syms)
            if len(syms):
                verb = 'was' if len(syms) == 1 else 'were'
                printWarning("There " + verb + " " + str(len(syms)) + " (skipped) broken symlinks in " + entry)
                self.list_broken_symlinks()

    def pop_broken_symlinks(self):
        if self.broken_syms:
            printDebug("Popping broken symlinks from %s for %s" % (self.path_stash, self.name))
            for origin, temp_target in self.broken_syms.items():
                try:
                    shutil.move(temp_target, origin)
                except OSError as err:
                    printError("Could not restore stashed broken symlink: " + origin)
                    printError("(%s)" % err.strerror)
            self.broken_syms.clear()

    def list_broken_symlinks(self):
        if self.broken_syms:
            for symlink in self.broken_syms.keys():
                printWarning(symlink)

    def store_md5(self, filepath):
        self.path_md5 = os.path.join(self.path_result_dir, "md5.sum")
        if not os.path.exists(filepath):
            return False

        h = hashlib.md5(open(filepath, 'rb').read())
        hashh = h.hexdigest()
        myfile = open(self.path_md5, 'a')
        wr = csv.writer(myfile, delimiter=";")
        wr.writerow([hashh, get_leaf_from_path(filepath)])
        myfile.close()

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

        # exclude_endings; only Pycharm-PEP8 warning
        if filenamefull.endswith(tuple(self.exclude_endings)):
            printDebug("Global exclude ending: %s" % filenamefull)
            return retval_skip
        elif filenamefull.endswith(tuple(self.exclude_endings)):
            printDebug("User exclude ending: %s" % filenamefull)
            return retval_skip

        #  exclude_files; only Pycharm-PEP8 warning
        elif get_leaf_from_path(filenamefull) in self.exclude_files:
            printDebug("Global exclude file: %s" % filenamefull)
            return retval_skip
        elif get_leaf_from_path(filenamefull) in self.exclude_files:
            printDebug("User exclude file: %s" % filenamefull)
            return retval_skip

        # exclude_dir_names; only Pycharm-PEP8 warning
        ll = getsub_dir_path(root_dir, filenamefull)
        if any(dirname in ll.split("/") for dirname in self.configs_global.exclude_dir_names):
            printDebug("Global exclude dir names matched at: %s" % filenamefull)
            return retval_skip
        if any(dirname in ll.split("/")[1:] for dirname in self.exclude_dir_names):
            printDebug("User exclude dir names matched at: %s" % filenamefull)
            return retval_skip

        # exclude_dir_fullpath (only user exclude); only Pycharm-PEP8 warning
        if any(dirname in filenamefull for dirname in self.exclude_dir_fullpath):
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

    def compress_pre(self):
        """" Checks and prints backup entry processing """
        printLog("--------------------------------------------------")
        if not self.enabled:
            printLog("Backup task \"%s\" is DISABLED --> SKIPPING" % self.name)
            return False
        printLog("Executing backup task: \"" + colorblue + self.name + colorreset + "\"")
        if filter_nonexistent_include_dirs(self.include_dirs) and self.skip_if_directory_nonexistent:
            printWarning("Skipping '" + self.name + "'")
            return False
        if not self.include_dirs:
            printWarning("Backup task \"%s\" include_dir pathes are all invalid --> SKIPPING" % self.name)
            return False
        if os.path.isfile(self.archivefullpath):
            printWarning("There is already an archive with this name:")
            printWarning("%s" % self.archivefullpath)
            printWarning("Skipping '" + self.name + "'")
            return False
        if self.skip_if_permission_fail:
            printLog("Pre-flight permission checks (Skip_If_Permission_Fail: True, FollowSymlinks: " + str(self.followsym) + ")")
            exit_flag = False
            for include_dir in self.include_dirs:
                unreadable_files = get_unreadable_files_in_recursive_subdir(include_dir, self.followsym)
                if unreadable_files:
                    printWarning("Ureadeable files in " + include_dir + ":")
                    printWarning(unreadable_files)
                    exit_flag = True
            if exit_flag:
                printWarning("Skipping '" + self.name + "'")
                return False

        if not os.path.isdir(self.path_result_dir):
            comment = "Result directory does not exists: %s" % self.path_result_dir
            exit_config_error(self.path_config_file, self.section, comment)
        printLog("Creating archive: %s" % self.archivefullpath)
        printLog("Compressing method: %s" % self.method)
        printLog("Free space in target dir: %s" % get_dir_free_space(self.path_result_dir))
        return True

    def compress_tar(self):
        """ Compressing with tar/targz method """
        archive = ""
        try:
            mode = ""
            if self.method == "tar":
                mode = "w"
            elif self.method == "targz":
                mode = "w:gz"
            elif self.method == "tarbz2":
                mode = "w:bz2"
            else:
                comment = ["Wrong compression method declared (%s)" % self.method,
                           "method = { tar ; targz ; tarbz2; zip}"]
                exit_config_error(self.path_config_file, self.section, comment)  # TODO: class-ification

            # http://stackoverflow.com/a/39321142/4325232
            # dereference = True if self.followsym else False      # TODO: remove if it does not needed
            archive = tarfile.open(name=self.archivefullpath, mode=mode, dereference=self.followsym)

            if self.withpath:
                for entry in self.include_dirs:
                    if self.followsym:  # workaround for "tar + follow symlinks + broken symmlinks" use case
                        self.stash_broken_symlinks(entry, self.get_broken_syms_in_recursive_subdir(entry))
                    archive.add(entry, filter=lambda x: self.filter_general(x, os.path.dirname(entry)))
                    if self.followsym:
                        self.pop_broken_symlinks()
            elif not self.withpath:
                for entry in self.include_dirs:
                    self.stash_broken_symlinks(entry, self.get_broken_syms_in_recursive_subdir(entry))
                    # http://stackoverflow.com/questions/39438335/python-how-could-i-access-tarfile-adds-name-parameter-in-adds-filter-me
                    archive.add(entry, arcname=os.path.basename(entry), filter=lambda x: self.filter_general(x, os.path.dirname(entry)))
                    self.pop_broken_symlinks()
            else:
                printError("Wrong 'withpath' config value! Should be \"yes\" / \"no\". Exiting.")
                sys.exit(1)
        except (IOError, OSError) as err:
            if err.errno == errno.EACCES:
                printError("OSError: %s on %s" % (os.strerror(err.errno), self.archivefullpath))
                sys.exit(err.errno)
            if err.errno == errno.ENOSPC:
                printError("OSError: No space on disk")
                sys.exit(err.errno)
            if err.errno == errno.ENOENT:
                # My ticket: http://stackoverflow.com/questions/39545741/python-tarfile-add-how-to-avoid-exception-in-case-of-follow-symlink-broken
                # Broken symlink skipping is resolved by stashing
                printError("OSError: broken symlink or can not find file")
                sys.exit(err.errno)
            else:
                printError("IOError/OSError: Unhandled exception: %s" % err.strerror)
                sys.exit(99)
        finally:
            archive.close()
            self.store_md5(self.archivefullpath)
            self.pop_broken_symlinks()

        filesize = os.path.getsize(self.archivefullpath)
        printOK("Done [%s]" % sizeof_fmt(filesize))

    def compress_zip(self):
        """ Compressing with zip method """
        archive = ""
        try:
            archive = zipfile.ZipFile(file=self.archivefullpath, mode="w", compression=zcompression)
            # archive.comment = self.description            # TODO: need to add description?
        except (IOError, OSError) as err:
            if archive:
                archive.close()
            if err.errno == errno.EACCES:
                printError("OSError: Can't write to this file: %s" % self.archivefullpath)
                sys.exit(err.errno)
            elif err.errno == errno.ENOSPC:
                printError("IOError/OSError: No space on disk")
                sys.exit(err.errno)
            else:
                printError("IOError/OSError: Unhandled error: %s" % err.strerror)
                sys.exit(99)

        # filtering + adding procedure starts by walking through on every file path
        for entry in self.include_dirs:
            for subdir, dirs, files in os.walk(top=entry, followlinks=True):
                for filename in files:
                    dirpart = getsub_dir_path(entry, subdir)
                    if self.filter_general(os.path.join(subdir, filename), entry):
                        file_fullpath = os.path.join(subdir, filename)

                        if self.check_if_symlink_broken(file_fullpath):
                            printWarning("broken symlink (skip): %s" % file_fullpath)
                            continue

                        try:
                            if self.withpath:
                                archive.write(filename=file_fullpath, compress_type=zcompression)
                            elif not self.withpath:
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
                                printLog("OSError: No such file or directory to compress: %s" % self.archivefullpath)
                                continue
                            else:
                                printLog("Unhandled IOError/OSError: %s" % err.strerror)
                                continue
        if archive:
            archive.close()
            self.store_md5(self.archivefullpath)
        filesize = os.path.getsize(self.archivefullpath)
        printOK("Done [%s]" % sizeof_fmt(filesize))


class Backupy:
    """ Backupy class """
    def __init__(self):
        self.validate = False
        self.path_home = os.path.expanduser("~")
        self.path_default_configdir = os.path.join(self.path_home, '.config/backupy')
        self.path_default_config_file = os.path.join(self.path_default_configdir, 'default.cfg')

        if len(sys.argv) == 2:
            if sys.argv[1] == "--help":
                self.help()
                sys.exit(0)
            # if sys.argv[1] == "--validate":  # TODO: validate
            #     self.validate = True
            #     sys.exit(0)
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

        printLog("backupy v" + __version__ + " starting")
        if debug:
            printWarning("DEBUG MODE ENABLED")
        self.backupset_list = []
        self.backupset_list.append(Backupset(self.path_config_file))

    def __del__(self):
        pass

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
              "   [BACKUP1]                            # Mandatory name pattern: BACKUP[1-99] (99 max) ; don't write anything after the number\n"
              "  *name = My Document backup            # write entry name here\n"
              "  *enabled = yes                        # is this backup active. {yes, no}\n"
              "  *archive_name = document_backup       # archive file name without extension\n"
              "  *path_result_dir = /home/joe/mybackups     # Where to create the archive file\n"
              "  *method = targz                       # Compression method {tar, targz, tarbz2, zip}\n"
              "  *followsym = yes                      # Should compressor follow symlinks\n"
              "  *withpath = no                        # compress files with or without full path\n"
              "  *skip_if_permission_fail = no         # skips backup task if there is/are file(s) with no access by running user\n"
              "  *skip_if_directory_nonexistent = no   # skips backup task if there is/are non-existent include_dir\n"
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
              "Tip 1: Don't forget to set 'enabled' to 'yes' if you want a backup entry to be active!\n"
              "Tip 2: use of comment sign '#' is allowed - at the end of option lines\n"
              "Tip 3: 'exclude_endings' special case: '~'  It excludes file endings like 'myfile.doc~'  (NOT myfile.~) \n"
              "Tip 4: 'exclude_dir_names' are active only _below_ the included directory's root path\n")
        if not os.path.exists(self.path_default_config_file):
            printWarning("You did not run backupy init yet.")
            printWarning("Just run ./backupy.py and let it create default config for you.\n")

    def create_config_file(self):
        # TODO: store config lines in a fix order
        # http://stackoverflow.com/questions/9001509/how-can-i-sort-a-dictionary-by-key
        filehandler = ""
        cfghandler = configparser.ConfigParser()
        cfghandler['GLOBAL_EXCLUDES'] = {'exclude_endings': '~, swp',
                                         'exclude_files': 'Thumbs.db, abcdefgh.txt',
                                         'exclude_dir_names': 'my_globaly_exclude_dir'}
        for i in range(1, 4):
            cfghandler['BACKUP' + str(i)] = {'name': 'Document backup' + str(i) + '           # comments are allowed',
                                             'enabled': 'no',
                                             'archive_name': 'document_backup' + str(i),
                                             'result_dir': '/home/joe/mybackups',
                                             'method': 'targz',
                                             'followsym': 'yes',
                                             'withpath': 'no',
                                             'skip_if_permission_fail': 'no',
                                             'skip_if_directory_nonexistent': 'no',
                                             'include_dir1': '/home/joe/humour                # at least one is mandatory',
                                             'include_dir2': '/home/joe/novels',
                                             'exclude_dir_names': 'garbage, temp',
                                             'exclude_dir_fullpath': '/home/joe/humour/saskabare, /home/joe/novels/bad_ones',
                                             'exclude_endings': '~, gif, jpg, bak',
                                             'exclude_files': 'abc.log, swp.db'}
        try:
            filehandler = open(self.path_default_config_file, "w")
            cfghandler.write(filehandler, space_around_delimiters=True)
        except OSError as err:
            printError("Cannot create config file: %s" % self.path_default_config_file)
            printError("Error: %s" % err.strerror)
            sys.exit(1)
        finally:
            filehandler.close()

    def check_first_run(self):
        if not os.path.exists(self.path_home):
            printError("Can not access home directory: %s" % self.path_home)
            sys.exit(1)
        if not os.path.exists(self.path_default_configdir):
            try:
                os.makedirs(name=self.path_default_configdir, exist_ok=True)
            except OSError as err:
                printError("Cannot create user config dir: %s" % self.path_default_configdir)
                printError("(%s)" % err.strerror)
                sys.exit(1)
        if not os.path.exists(self.path_default_config_file):
            printLog("First run!")
            printLog("Generating default config file: %s" % self.path_default_config_file)
            self.create_config_file()
            printLog("---------------------------------------------------------------")
            printLog("Now you can create user specified backup entries in %s" % self.path_default_config_file)
            printLog("Also you can create custom user specified backup-set config file(s) - called as command line parameter.")
            printLog("Don't forget to set 'enabled' to 'yes' if you want a backup entry to be active!\n")
            printWarning("backupy.py --help is your friend.\n")
            sys.exit(0)

    def execute_backupsets(self):
        for backupset in self.backupset_list:
            backupset.execute()
        printLog("--------------------------------------------------")
        printLog("backupy finished")


def main():
    check_python_version()
    backupy = Backupy()
    backupy.check_first_run()
    backupy.execute_backupsets()


if __name__ == '__main__':
    sys.exit(main())
