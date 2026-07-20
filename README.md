**backupy** is a handy backup tool written in python 3

License: GPLv3

Copyright 2026, Balint Fekete

## Feature list ##

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
    * result dir
    * create date-format subdir in result dir
    * compression method (tar, targz, tarbz2, zip)
    * store files/directories with/without full path
    * follow symlinks (yes/no)
    * include directories (multiple entries)
    * exclude directory names
    * exclude directory with fullpath
    * exclude filenames
    * exclude filetypes (special: '~'  →  mynovel.doc\~ )
    * skip task if permission fail
    * skip task if directory is non-existent


## Basics ##

### Set up, get repo ###

```
git clone https://github.com/kaktusztea/backupy.git
```


### Help ###

```
./backupy.py --help
```


### Initial configuration: creating default.toml ###

```
./backupy.py
```


### customize default backup set and start backup ###

```
vi ~/.config/backupy/default.toml   (customize)
./backupy.py   (start backup with default backup set)
```


### create custom backup set and start backup ###

```
cp ~/.config/backupy/default.toml /my/path/mybackup.toml
vi /my/path/mybackup.toml   (customize)
./backupy.py /my/path/mybackup.toml
```

## Planned features ##

- exclude / include unique files
- `[HOME_CONFIGS]` unique backup section
- pre-calculate estimated file size → predict if free space will be enough or not

## Contact ##
If you have comments, found a bug or just want to explain how awesome this script is :) - write a mail:


```
kaktusztea _ at_ protonmail _ dot_ com
```
