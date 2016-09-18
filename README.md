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
    * exclude filetypes (special: '~' ==> mynovel.doc~ )
    * result dir
 
## Basics ##

### Set up ###

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

## Contact ##
If you have comments, found a bug or just want to explain how awesome this script is :) - write a mail:


```
#!bash

kaktusztea _ at_ protonmail _ dot_ ch
```