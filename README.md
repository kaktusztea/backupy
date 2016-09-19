**backupy** is a handy backup tool written in python 3.4.

License: GPLv3

Copyright 2016, Balint Fekete

## Feature list ##

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
    * exclude filetypes (special: '~'  →  mynovel.doc~ )
    * result dir

## Known issues ##
* (tar/targz/tarbz2 compress method + follow symlink + broken symlink) combo causes unhandled exception 
   ( http://stackoverflow.com/questions/39545741/python-tarfile-add-how-to-avoid-exception-in-case-of-follow-symlink-broken )

* follow symlink does not work with zip compression (old zip standard doesn't support it, will try to hack it anyway :)
 
## Basics ##

### Set up, get repo ###

```
#!bash

git clone https://bitbucket.org/kaktusztea/backupy.git
```


### Help ###

```
#!bash

./backupy.py --help
```


### Initial configuration: creating default.cfg ###

```
#!bash

./backupy.py
```


### customize default backup set and start backup ###

```
#!bash

vi ~/.config/backupy/default.cfg   (customize)
./backupy.py   (start backup with default backup set)
```


### create custom backup set and start backup ###

```
#!bash

cp ~/.config/backupy/default.cfg /my/path/mybackup.cfg
vi /my/path/mybackup.cfg   (customize)
./backupy.py /my/path/mybackup.cfg

```

## Planned features ##
* exclude / include unique files

* 7zip/lz support

* META section
  
```
#!bash
   [META]
   description = "This is my set for weekly data backup"
   author = myuser
   creation_date = 2016-09-01
```


* [HOME_CONFIGS] unique backup section

* remote compression target (ssh, etc)

* reserve and move n previous backups

* comment file addition to archive (zip)

* filelist file creation from archive - after compression

* create md5sum from archive file

* pre-calculate estimated file size → predict if free space will be enough or not

* logging


## Contact ##
If you have comments, found a bug or just want to explain how awesome this script is :) - write a mail:


```
#!bash

kaktusztea _ at_ protonmail _ dot_ ch
```