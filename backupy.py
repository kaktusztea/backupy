#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    backupy: a handly tool for selectively backup your data

    Features:

    * backup sets are separatable in unique config files
    * multiple config files as parameters - able to execute them in one batch (in sequence)
    * unique backup tasks in backup sets
    * global exclude lists (file, dir, filetype) for entire backup set
    * handling broken symlinks for "tar+follow syms+broken syms" use case
    * validate mode: only config file validation, no execution
    * create md5sum from archive file
    * every backup task is customizable
        * enabled / disabled
        * archive file name
        * compression method (tar, targz, tarbz2, zip)
        * store files/directories with/without full path
        * follow symlinks (true/false)
        * include directories (multiple entries)
        * exclude directory names
        * exclude directory with fullpath
        * exclude filenames
        * exclude filetypes (special: '~' → mynovel.doc~ )
        * result dir
        * skip task if permission fail
        * skip task if directory is non-existent
"""

import os
import sys
import csv
import time
import errno
import shutil
import hashlib
import tarfile
import zipfile
import datetime
import argparse
try:
    import tomllib
except ModuleNotFoundError:
    print("ERROR: Python 3.12+ is required (tomllib not available).")
    sys.exit(1)
from pathlib import Path
try:
    import zlib
    zcompression = zipfile.ZIP_DEFLATED
except ImportError:
    zcompression = zipfile.ZIP_STORED

# Globals
__author__ = 'Balint Fekete'
__copyright__ = 'Copyright 2026, Balint Fekete'
__license__ = 'GPLv3'
__version__ = '2.0.0'
__maintainer__ = 'Balint Fekete'
__email__ = 'kaktusztea at_ protonmail dot_ com'
__status__ = 'Production'


def strip_dash_string_end(line):
    while line.endswith("/"):
        line = line[:-1]
    return line


def strip_enddash_on_list(endinglist):
    for idx, elem in enumerate(endinglist):
        while elem.endswith("/"):
            elem = elem[:-1]
        endinglist[idx] = elem
    return endinglist


def add_dot_for_endings(endinglist):
    for idx, elem in enumerate(endinglist):
        if not elem.startswith(".") and elem != "~":
            endinglist[idx] = "." + elem
    return endinglist


def getsub_dir_path(root, longpath):
    if not root.startswith("/") or not longpath.startswith("/"):
        raise ValueError(f"getsub_dir_path: both paths must be absolute (got root={root!r}, longpath={longpath!r})")
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
            printWarning(f"Include dir doesn't exist, skipping: {dirpath}")
    remove_indexes.sort(reverse=True)
    if remove_indexes:
        for index in remove_indexes:
            del include_dirs[index]
        return True    # there was at least one unaccessable dir


def create_dir(path):
    try:
        os.makedirs(name=path, exist_ok=True)
    except OSError as err:
        printError(f"Cannot create dir: {path}")
        printError(f"({err.strerror})")
        return False
    return True


def check_if_file_is_unreadable(path):
    return not os.access(path, os.R_OK)


def get_unreadable_files_in_recursive_subdir(subdir, followsym):
    lista = []
    for root, dirs, files in os.walk(subdir):
        for file in files:
            ffile = os.path.join(root, file)
            if not followsym and os.path.islink(ffile):
                continue
            if check_if_file_is_unreadable(ffile):
                lista.append(ffile)
    return lista


def get_date():
    return datetime.datetime.now().strftime('%Y-%m-%d')


def get_time():
    return datetime.datetime.now().strftime('[%H:%M:%S]')


def get_time_short():
    return datetime.datetime.now().strftime('%H%M')


def printLog(log, pre_empty_lines=0):
    pp = "\n" * pre_empty_lines + get_time() + " " + str(log)
    print(pp)


def printWarning(log):
    if isinstance(log, str):
        printLog(Colors.coloryellow + log + Colors.colorreset)
    if isinstance(log, list):
        for line in log:
            printLog(" " + Colors.coloryellow + line + Colors.colorreset)


def printError(log):
    printLog(Colors.colorred + str(log) + Colors.colorreset)


def printDebug(log):
    if Backupy.debug:
        printLog(Colors.coloryellow + str(log) + Colors.colorreset)


def printOK(log):
    printLog(Colors.colorgreen + str(log) + Colors.colorreset)


def exit_config_error(config_file, section, comment, exitnow=True):
    printError(f"{config_file}")
    printError(f"[{section}]")
    if isinstance(comment, str):
        printError(comment)
    if isinstance(comment, list):
        for line in comment:
            printError(line)
    if exitnow:
        sys.exit(1)


def sizeof_fmt(num, suffix='B'):
    """ returns with human readable byte size format """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def get_dir_free_space(dirname):
    """ returns directory's free space in human readable format """
    st = os.statvfs(dirname)
    return sizeof_fmt(st.f_bavail * st.f_frsize)


class Colors:
    colorred = '\033[1;31m'
    colorreset = '\033[0m'
    coloryellow = '\033[0;93m'
    colorblue = '\033[1;2;34m'
    colorgreen = "\033[1;32m"
    colorbold = "\033[1m"


class Configglobal:
    def __init__(self):
        self.exclude_files = []
        self.exclude_endings = []
        self.exclude_dir_names = []


class BackupyTarfile(tarfile.TarFile):
    """ Override default built-in python tarfile library's add method
        to handle permission read errors and be able to skip intead of
        immediate exception.
    """
    def add(self, name, arcname=None, recursive=True, exclude=None, *, filter=None):
        self._check("aw")

        if arcname is None:
            arcname = name

        # Exclude pathnames.
        if exclude is not None:
            import warnings
            warnings.warn("use the filter argument instead", DeprecationWarning, 2)
            if exclude(name):
                self._dbg(2, f"tarfile: Excluded {name!r}")
                return

        # Skip if somebody tries to archive the archive...
        if self.name is not None and os.path.abspath(name) == self.name:
            self._dbg(2, f"tarfile: Skipped {name!r}")
            return

        self._dbg(1, name)

        # Create a TarInfo object from the file.
        try:
            tarinfo = self.gettarinfo(name, arcname)
        except FileNotFoundError:
            printWarning(f"Skip file (broken symlink): {name}")
            return

        if tarinfo is None:
            self._dbg(1, f"tarfile: Unsupported type {name!r}")
            return

        # Change or exclude the TarInfo object.
        if filter is not None:
            tarinfo = filter(tarinfo)
            if tarinfo is None:
                self._dbg(2, f"tarfile: Excluded {name!r}")
                return

        # Append the tar header and data to the archive.
        if tarinfo.isreg():
            try:
                with open(name, "rb") as f:
                    self.addfile(tarinfo, f)
            except PermissionError:
                printWarning(f"Skip file (permission error): {name}")
                return
            except FileNotFoundError:
                printWarning(f"Skip file (broken symlink): {name}")
                return

        elif tarinfo.isdir():
            self.addfile(tarinfo)
            if recursive:
                try:
                    for f in os.listdir(name):
                        self.add(os.path.join(name, f), os.path.join(arcname, f), recursive, exclude, filter=filter)
                except PermissionError as err:
                    printWarning(f"Skip directory (permission error): {name}")
                    return
        else:
            self.addfile(tarinfo)


class Backupset:
    def __init__(self, config_file):
        if not os.path.exists(config_file):
            printError(f"Config file does not exists: {config_file}")
            sys.exit(1)
        self.config_file = config_file
        self.name = ""
        self.description = ""
        self.enabled = False
        self.task_list = []
        self.g = Configglobal()
        # parse config
        self._load_config()
        printLog(f"Backup set config file is valid ({self.name}): {self.config_file}")

    def _load_config(self):
        METHOD_EXTENSIONS = {
            'tar': '.tar',
            'targz': '.tar.gz',
            'tarbz2': '.tar.bz2',
            'tarxz': '.tar.xz',
            'zip': '.zip',
        }

        try:
            with open(self.config_file, "rb") as f:
                cfg = tomllib.load(f)
        except tomllib.TOMLDecodeError as err:
            printError(f"Config file syntax error: {self.config_file}")
            printError(f"{err}")
            sys.exit(1)
        except OSError as oerr:
            printError(f"Cannot read config file: {self.config_file}")
            printError(f"{oerr.strerror} ({oerr.errno})")
            sys.exit(1)

        try:
            # [meta]
            meta = cfg["meta"]
            self.name = meta["name"]
            self.description = meta.get("description", "")
            self.enabled = meta["enabled"]

            # [global_excludes]
            glb = cfg.get("global_excludes", {})
            self.g.exclude_endings = add_dot_for_endings(list(glb.get("endings", [])))
            self.g.exclude_files = list(glb.get("files", []))
            self.g.exclude_dir_names = strip_enddash_on_list(list(glb.get("dir_names", [])))

            # [[backup]]
            for idx, section in enumerate(cfg.get("backup", [])):
                section_name = f"backup[{idx}]"
                task = Backuptask(section_name, self.g, self.config_file)
                task.section = section_name
                task.enabled = section["enabled"]
                task.name = section["name"]
                task.archive_name = section["archive_name"]
                task.create_target_date_dir = section["create_target_date_dir"]
                task.path_result_dir = section["result_dir"]
                task.method = section["method"]
                task.followsym = section["followsym"]
                task.withpath = section["withpath"]
                task.skip_if_permission_fail = section["skip_if_permission_fail"]
                task.skip_if_directory_nonexistent = section["skip_if_directory_nonexistent"]

                task.include_dirs = strip_enddash_on_list(list(section["include_dirs"]))
                task.exclude_dir_fullpath = strip_enddash_on_list(list(section.get("exclude_dir_fullpaths", [])))
                task.exclude_dir_names = strip_enddash_on_list(list(section.get("exclude_dir_names", [])))
                task.exclude_endings = add_dot_for_endings(list(section.get("exclude_endings", [])))
                task.exclude_files = list(section.get("exclude_files", []))

                # precompute merged exclude lists (global + task)
                task._all_endings = tuple(self.g.exclude_endings + task.exclude_endings)
                task._all_files = self.g.exclude_files + task.exclude_files

                # archive filename with timestamp + extension
                if task.archive_name.strip() == '':
                    exit_config_error(self.config_file, section_name, "'archive_name' is mandatory.")
                if task.method not in METHOD_EXTENSIONS:
                    exit_config_error(self.config_file, section_name,
                                      [f"Wrong compression method declared ({task.method})",
                                       f"method = {{ {' ; '.join(METHOD_EXTENSIONS)} }}"])
                task.archive_name += f"_{get_date()}_{get_time_short()}{METHOD_EXTENSIONS[task.method]}"

                # result dir with optional date subdir
                if task.enabled and task.create_target_date_dir:
                    task.path_result_dir = os.path.join(task.path_result_dir, get_date())

                task.archivefullpath = os.path.join(task.path_result_dir, task.archive_name)

                if not task.check_include_dir_dups:
                    exit_config_error(self.config_file, section_name, "'include_dirs' duplicates are not allowed.")

                self.task_list.append(task)

        except KeyError as err:
            printError(f"Invalid config file: {self.config_file}")
            printError(f"Missing key: {err}")
            sys.exit(1)

        if not self.check_archivename_unique():
            exit_config_error(self.config_file, "General error", "'result_dir' + 'archive_name' + 'method' combo and 'name' should be unique between enabled backup tasks!")

    def check_archivename_unique(self):
        enabled = [t for t in self.task_list if t.enabled]
        names = [t.name for t in enabled]
        archive_keys = [(t.path_result_dir, t.archive_name) for t in enabled]
        return len(names) == len(set(names)) and len(archive_keys) == len(set(archive_keys))

    def has_active_backuptask(self):
        return any(task.enabled for task in self.task_list)

    def execute(self):
        if not self.enabled:
            printLog(f"Backup set \"{self.name}\" is DISABLED --> SKIPPING")
            printLog(Backupy.double_line)
            return False
        if not self.has_active_backuptask():
            printLog(Backupy.simple_line)
            printLog(f"You don't have any active backup task entries in {self.config_file}")
            printLog("Exiting.")
            return False
        for task in self.task_list:
            if task.compress_pre():
                printLog("Processing...")
                if task.method == "zip":
                    task.compress_zip()
                else:
                    task.compress_tar()
        printLog(Backupy.double_line)


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
        self.create_target_date_dir = True
        self.skip_if_permission_fail = False
        self.skip_if_directory_nonexistent = False
        self.include_dirs = []
        self.exclude_dir_fullpath = []
        self.exclude_dir_names = []
        self.exclude_endings = []
        self.exclude_files = []
        self.configs_global = cglobal

        self.path_config_file = path_config_file
        self.path_md5 = ''

    @property
    def check_include_dir_dups(self):
        return len(self.include_dirs) == len(set(self.include_dirs))

    @staticmethod
    def check_if_symlink_broken(path):
        return os.path.islink(path) and not os.path.exists(path)

    def store_md5(self, filepath):
        self.path_md5 = os.path.join(self.path_result_dir, "md5.sum")
        if not os.path.exists(filepath):
            return False

        # generate hash
        printLog("Generating hash")
        hash_value = hashlib.md5()
        with open(filepath, "rb") as hash_handler:
            for chunk in iter(lambda: hash_handler.read(2 ** 20), b''):
                hash_value.update(chunk)
        hash_result = hash_value.hexdigest()
        printLog(hash_result)

        # write hash to csv file: hash, filesize, filename
        with open(self.path_md5, 'a') as myfile:
            wr = csv.writer(myfile, delimiter=";")
            wr.writerow([hash_result, os.path.getsize(filepath), Path(filepath).name])

    def _is_excluded(self, filenamefull, root_dir):
        """Returns True if the file should be excluded."""
        if self._all_endings and filenamefull.endswith(self._all_endings):
            printDebug(f"Exclude ending matched: {filenamefull}")
            return True
        if Path(filenamefull).name in self._all_files:
            printDebug(f"Exclude file matched: {filenamefull}")
            return True
        parts = getsub_dir_path(root_dir, filenamefull).split("/")
        if any(d in parts for d in self.configs_global.exclude_dir_names):
            printDebug(f"Global exclude dir names matched at: {filenamefull}")
            return True
        if any(d in parts[1:] for d in self.exclude_dir_names):
            printDebug(f"Task exclude dir names matched at: {filenamefull}")
            return True
        if any(dirname in filenamefull for dirname in self.exclude_dir_fullpath):
            printDebug(f"Exclude dir fullpath matched at: {filenamefull}")
            return True
        return False

    def filter_tar(self, item, root_dir):
        """tarfile filter callback: returns TarInfo or None."""
        return None if self._is_excluded(os.path.join(root_dir, item.name), root_dir) else item

    def compress_pre(self):
        """Pre-flight checks before compression. Returns True if task can proceed."""
        skip = f"Skipping backup task '{self.name}'"
        printLog(Backupy.simple_line)

        if not self.enabled:
            printLog(f"Backup task \"{self.name}\" is DISABLED --> SKIPPING")
            return False

        printLog(f"Executing backup task: \"{Colors.colorblue}{self.name}{Colors.colorreset}\"")

        if self.method == "zip" and self.followsym:
            printWarning("'Method: zip' is incompatible with 'followsym = true'. Zip cannot follow symlinks. Sad.")
            return False

        if not create_dir(self.path_result_dir):
            printWarning(skip)
            return False

        if filter_nonexistent_include_dirs(self.include_dirs) and self.skip_if_directory_nonexistent:
            printWarning(f"{skip} (skip_if_directory_nonexistent is set)")
            return False

        if not self.include_dirs:
            printWarning(f"{skip} (all include_dirs are invalid)")
            return False

        if os.path.isfile(self.archivefullpath):
            printWarning(f"Archive already exists: {self.archivefullpath}")
            printWarning(skip)
            return False

        if self.skip_if_permission_fail:
            printLog(f"Pre-flight permission checks (followsym: {self.followsym})")
            unreadable_found = False
            for include_dir in self.include_dirs:
                unreadable_files = get_unreadable_files_in_recursive_subdir(include_dir, self.followsym)
                if unreadable_files:
                    printWarning(f"Unreadable files in {include_dir}:")
                    printWarning(unreadable_files)
                    unreadable_found = True
            if unreadable_found:
                printWarning(skip)
                return False

        printLog(f"Creating archive: {self.archivefullpath}")
        printLog(f"Compressing method: {self.method}")
        printLog(f"Free space in target dir: {get_dir_free_space(self.path_result_dir)}")
        return True

    def compress_tar(self):
        """ Compressing with tar/targz method """
        TAR_MODES = {'tar': 'w', 'targz': 'w:gz', 'tarbz2': 'w:bz2', 'tarxz': 'w:xz'}
        mode = TAR_MODES[self.method]

        try:
            # http://stackoverflow.com/a/39321142/4325232
            with BackupyTarfile.open(name=self.archivefullpath, mode=mode, dereference=self.followsym) as archive:
                for entry in self.include_dirs:
                    arcname = entry if self.withpath else os.path.basename(entry)
                    root_dir = os.path.dirname(entry)
                    archive.add(entry, arcname=arcname, filter=lambda x, r=root_dir: self.filter_tar(x, r))

        except OSError as err:
            match err.errno:
                case errno.ENOSPC:
                    printError("No space on disk")
                case errno.EACCES:
                    printError(f"Permission denied: {self.archivefullpath}")
                case _:
                    printError(f"OSError: {err.strerror} ({self.archivefullpath})")
            sys.exit(err.errno or 99)

        self.store_md5(self.archivefullpath)
        printOK(f"Done [{sizeof_fmt(os.path.getsize(self.archivefullpath))}]")

    def compress_zip(self):
        """ Compressing with zip method """
        try:
            with zipfile.ZipFile(file=self.archivefullpath, mode="w", compression=zcompression) as archive:
                for entry in self.include_dirs:
                    for subdir, dirs, files in os.walk(top=entry, followlinks=True):
                        for filename in files:
                            file_fullpath = os.path.join(subdir, filename)

                            if self._is_excluded(file_fullpath, entry):
                                continue
                            if self.check_if_symlink_broken(file_fullpath):
                                printWarning(f"broken symlink (skip): {file_fullpath}")
                                continue

                            arcname = file_fullpath if self.withpath else os.path.join(getsub_dir_path(entry, subdir), filename)
                            try:
                                archive.write(filename=file_fullpath, arcname=arcname)
                            except UnicodeEncodeError:
                                printWarning(f"Skip file (name encoding problem): {subdir}")
                            except PermissionError:
                                printWarning(f"Skip file (permission error): {file_fullpath}")
                            except OSError as err:
                                printWarning(f"Skip file ({err.strerror}): {file_fullpath}")

        except OSError as err:
            match err.errno:
                case errno.ENOSPC:
                    printError("No space on disk")
                case errno.EACCES:
                    printError(f"Permission denied: {self.archivefullpath}")
                case _:
                    printError(f"OSError: {err.strerror} ({self.archivefullpath})")
            sys.exit(err.errno or 99)

        self.store_md5(self.archivefullpath)
        printOK(f"Done [{sizeof_fmt(os.path.getsize(self.archivefullpath))}]")


class Backupy:
    """ Backupy class """
    debug = False
    simple_line = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    double_line = "==========================================================="

    def __init__(self, pargs):
        self.start_time = time.time()
        self.validate = False
        self.path_home = os.path.expanduser("~")
        self.path_default_configdir = os.path.join(self.path_home, '.config/backupy')
        self.path_default_config_file = os.path.join(self.path_default_configdir, 'default.toml')
        self.backupset_list = []
        self.path_config_files = []

        argparser = argparse.ArgumentParser(prog='backupy')
        argparser.add_argument('--manual', action='store_true', help='show backupy short manual')
        argparser.add_argument('--debug', action='store_true', help='run backupy in debug mode')
        argparser.add_argument('--validate', action='store_true', help='validate config files only, do not execute')
        argparser.add_argument('-s', '--backupsets', nargs='+', help='list of (backupset) config file pathes')

        args = argparser.parse_args(pargs)
        self.path_config_files = args.backupsets
        self.validate = args.validate
        Backupy.debug = args.debug

        if args.manual:
            self.show_manual()
            sys.exit(0)

        printLog("backupy v" + __version__ + " starting")
        if Backupy.debug:
            printWarning("DEBUG MODE")
        if self.validate:
            printWarning("VALIDATE MODE: only config check, no execution!")

        if not self.path_config_files:
            self.path_config_files = []
            self.path_config_files.append(self.path_default_config_file)
            self.check_first_run()

        for path in self.path_config_files:
            self.backupset_list.append(Backupset(os.path.abspath(path)))

        if self.validate:
            printOK("All config files are valid. Wo-hoooo!")
            sys.exit(0)

    def show_manual(self):
        print(f"""\
backupy v{__version__}

Start methods
   ./backupy.py                        # a.) at first run, generates default backup set config file
                                       # b.) if exists, starts with default config (~/.config/backupy/default.toml)
   ./backupy.py -s /foo/mybackup.toml  # starts with custom backup set config file
   ./backupy.py -s /foo/my.toml /bar/second.toml /boo/third.toml
                                       # starts with 3 config files for 3 different backup sets
   ./backupy.py --validate -s /foo/mybackup.toml /bar/second.toml
                                       # only validates config files, doesn't execute backup sets
   ./backupy.py --manual               # this short manual

Summary:
   - backupy handles backup sets - represented by .toml files
   - every backup set is built up from [[backup]] task entries
   - you can enable/disable backup sets and tasks via 'enabled' (true/false)

Example config file (TOML format)
   [meta]
   name = "My backup set"               # name of the backup set
   description = "For relaxed days :)"   # free text description
   enabled = true                        # is this backup set enabled

   [global_excludes]
   endings = ["~", ".swp"]               # globally excluded file extensions
   files = ["Thumbs.db", "temp.txt"]     # globally excluded filenames
   dir_names = ["trash", "garbage"]      # globally excluded directory names

   [[backup]]                            # each [[backup]] is one backup task (unlimited)
   name = "My Document backup"           # backup task name
   enabled = true                        # is this backup active
   create_target_date_dir = true         # creates YYYY-MM-DD subdir in result_dir
   archive_name = "document_backup"      # archive file name without extension
   result_dir = "/home/joe/backup"       # where to create the archive file
   method = "targz"                      # compression method: tar, targz, tarbz2, tarxz, zip
   followsym = true                      # should compressor follow symlinks
   withpath = false                      # compress files with or without full path
   skip_if_permission_fail = false       # skip task if file(s) are unreadable
   skip_if_directory_nonexistent = false  # skip task if include_dirs don't exist
   include_dirs = ["/home/joe/humour", "/home/joe/novels"]  # at least one mandatory
   exclude_dir_names = ["garbage", "temp"]
   exclude_dir_fullpaths = ["/home/joe/humour/saskabare"]
   exclude_endings = ["~", ".gif", ".jpg", ".bak"]
   exclude_files = ["abc.log", "Thumbs.db"]

Tips:
   - Set 'enabled = true' for backup sets and tasks you want active
   - Comments with '#' are supported natively in TOML
   - 'exclude_endings' special case: '~' excludes files like 'myfile.doc~'
   - 'exclude_dir_names' are active only below the included directory's root path
""")
        if not os.path.exists(self.path_default_config_file):
            printWarning("You did not run backupy init yet.")
            printWarning("Just run ./backupy.py and let it create default config for you.\n")

    def print_elapsed_time(self):
        hours, rem = divmod(time.time() - self.start_time, 3600)
        minutes, seconds = divmod(rem, 60)
        printLog(f"Elapsed time: {int(hours):0>2}:{int(minutes):0>2}:{seconds:02.0f}", 1)

    def create_config_file(self):
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'default.toml')
        try:
            shutil.copy(template_path, self.path_default_config_file)
        except OSError as err:
            printError(f"Cannot create config file: {self.path_default_config_file}")
            printError(f"Error: {err.strerror}")
            sys.exit(1)

    def check_first_run(self):
        if not os.path.exists(self.path_home):
            printError(f"Can not access home directory: {self.path_home}")
            sys.exit(1)
        if not os.path.exists(self.path_default_configdir):
            try:
                os.makedirs(name=self.path_default_configdir, exist_ok=True)
            except OSError as err:
                printError(f"Cannot create user config dir: {self.path_default_configdir}")
                printError(f"({err.strerror})")
                sys.exit(1)
        if not os.path.exists(self.path_default_config_file):
            if self.validate:
                printError("There is no default config file or given as a parameter (-s). There is nothing to validate.")
                printError("You can create default config file by running backupy.py without parameteres.")
                sys.exit(1)
            printLog("First run!")
            printLog(f"Generating default config file: {self.path_default_config_file}")
            self.create_config_file()
            printLog(Backupy.simple_line)
            printLog(f"Now you can create user specified backup tasks in {self.path_default_config_file}")
            printLog("Also you can create custom user specified backup-set config file(s) - called as command line parameter.")
            printLog("Don't forget to set 'enabled = true' if you want a backup set or task to be active!\n")
            printWarning("Use 'backupy.py --help' for parameter help.")
            printWarning("Use 'backupy.py --manual' to show How-to page.\n")
            sys.exit(0)

    def execute_backupsets(self):
        for backupset in self.backupset_list:
            printLog(Backupy.double_line, 2)
            printLog(f"{Colors.colorblue}Executing backup set: {backupset.name}{Colors.colorreset} ")
            printLog(Backupy.double_line)
            backupset.execute()
        self.print_elapsed_time()
        printOK("backupy finished")


def main(args):
    backupy = Backupy(args)
    backupy.execute_backupsets()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
