#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'kaktusz'
import os
import sys
import errno
import ntpath
import tarfile
import datetime
import time
import zipfile
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

# == globals ==========================================
backupentry = {}
target = {}

G_EXCLUDE_ENDINGS = ['~', 'gif']
G_EXCLUDE_FILES = ['Thumbs.db', 'faja.txt']
G_EXCLUDE_DIRECTORIES = ['myexldirg']

C_EXCLUDE_ENDINGS = []
C_EXCLUDE_FILES = []
C_EXCLUDE_DIRECTORIES = []


# == methods =========================================

# get filename only from path
def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


# filter function for tar creation - general and custom
def filter_general(tarinfo):
    if tarinfo.name.endswith(tuple(G_EXCLUDE_ENDINGS)):
        return None
    elif tarinfo.name.endswith(tuple(C_EXCLUDE_ENDINGS)):
        return None
    elif path_leaf(tarinfo.name) in G_EXCLUDE_FILES:
        return None
    elif path_leaf(tarinfo.name) in C_EXCLUDE_FILES:
        return None
    elif path_leaf(tarinfo.name) in G_EXCLUDE_DIRECTORIES:
        return None
    elif path_leaf(tarinfo.name) in C_EXCLUDE_DIRECTORIES:
        return None
    else:
        return tarinfo


def getTime():
    now = datetime.datetime.now()
    nowstr = '[%02d:%02d:%02d]' % (now.hour, now.minute, now.second)
    return nowstr


def getDate():
    now = datetime.datetime.now()
    nowstr = '%04d-%02d-%02d' % (now.year, now.month, now.day)
    return nowstr


def compress_pre(t, bobject):
    filepath = os.path.join(t['path'], bobject['filename'])
    print(getTime()+" [Compressing (%s)] '%s' -> %s" % (bobject['method'], bobject['pathcompress'], filepath))
    if os.path.isfile(filepath):
        print('  [Skipping] There is already an archive with this name: %s' % filepath)
        return False
    return True


# == tar, tar.gz =======
def compress_tar(t, bobject):
    filepath = os.path.join(t['path'], bobject['filename'])
    try:
        mode = ""
        if bobject['method'] == "tar":
            mode = "w"
        elif bobject['method'] == "targz":
            mode = "w:gz"
        else:
            print("Wrong tar compress method. Exiting..")
            exit(4)

        archive = tarfile.open(filepath, mode)
        if bobject['withoutpath'] == 'no':
            archive.add(bobject['pathcompress'], filter=filter_general)
        elif bobject['withoutpath'] == 'yes':
            archive.add(bobject['pathcompress'], arcname=os.path.basename(bobject['pathcompress']), filter=filter_general)
        else:
            print("Wrong 'filepath' value! Exiting.")
            exit(2)
    except IOError as err:
        print("  [IOError] %s" % err.strerror)
        if err[0] == errno.EACCES:
            print("  [Skipping] Can't write to this file: %s" % filepath)
        elif err[0] == errno.ENOSPC:
            print("  [Exiting!]")
            exit(3)
        else:
            print("  [Previous exception is unhandled]")
    except OSError as err:
        if err[0] == errno.ENOENT:
            print("  [Skipping] No such file or directory to compress: %s" % bobject['pathcompress'])
            exit(4)
        else:
            print("  [Unhandled other OSError] %s]" % err.strerror)
    else:
        archive.close()
        filesize = os.path.getsize(filepath)
        print(" [Done] [%s KBytes]" % (filesize/1024))


# == zip ===============
def compress_zip(t, bobject):
    dirpath = bobject['pathcompress'] + "/*"
    filepath = os.path.join(t['path'], bobject['filename'])

    try:
        archive = zipfile.ZipFile(filepath, mode="w")                   # TODO: filtering!
        archive.comment = bobject['description']
        archive.write(dirpath, compress_type=compression)
    except IOError as err:
        print("  [IOError] %s" % err.strerror)
        if err[0] == errno.EACCES:
            print("  [Skipping] Can't write to this file: %s" % filepath)
        elif err[0] == errno.ENOSPC:
            print("  [Exiting!]")
            exit(3)
        else:
            print("  [Previous exception is unhandled]")
    except OSError as err:
        if err[0] == errno.ENOENT:
            print("  [Skipping] No such file or directory to compress: %s" % dirpath)
            exit(4)
        else:
            print("  [Unhandled other OSError] %s]" % err.strerror)
    else:
        archive.close()
        filesize = os.path.getsize(filepath)
        print(" [Done] [%s KBytes]" % (filesize/1024))


def init():
    print("[backupy 0.1] %s" % getDate())
    print("%s [Starting backup]" % getTime())

    backupentry.update({'description'        : 'temp backup'})
    backupentry.update({'method'             : 'zip'})
    backupentry.update({'withoutpath'        : 'no'})
    backupentry.update({'filename'           : 'temp'})
    backupentry.update({'pathcompress'       : '/home/kaktusz/temp/dl'})
    backupentry.update({'followsym'          : 'yes'})
    backupentry.update({'exclude_endings'    : list(['~', 'gif'])})
    backupentry.update({'exclude_files'      : list(['ize.log', 'faja.txt'])})
    backupentry.update({'exclude_directories': list(['/home/kaktusz/temp/dl/myexldirc'])})
    backupentry.update({'include_directories': ''})

    if backupentry['method'] == 'tar':
        backupentry['filename'] += '_' + getDate() + '.tar'
    if backupentry['method'] == 'targz':
        backupentry['filename'] += '_' + getDate() + '.tar.gz'
    if backupentry['method'] == 'zip':
        backupentry['filename'] += '_' + getDate() + '.zip'

    target.update({'path': '/home/kaktusz/temp/backuptest'})

    # fill current exclude lists
    C_EXCLUDE_ENDINGS.extend(list(backupentry['exclude_endings']))
    C_EXCLUDE_FILES.extend(backupentry['exclude_files'])
    C_EXCLUDE_DIRECTORIES.extend(backupentry['exclude_directories'])


def main():
    init()

    mode = backupentry['method']
    if compress_pre(target, backupentry):
        if mode == "tar" or mode == "targz:":
            compress_tar(target, backupentry)
        elif mode == "zip":
            compress_zip(target, backupentry)
        else:
            print("Wrong method type. Exiting.")
            exit(1)

if __name__ == '__main__':
    # sys.exit(main(sys.argv[1]))
    sys.exit(main())
