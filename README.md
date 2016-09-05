**backupy** is a handy backup tool written in python 3.4.

## Feature list ##

* backup sets separatable in unique files (passed as command line parameter)
* unique backup entries in backup sets (up to 99)
* global exclude lists (file, dir, filetype) for entire backup set
* every backup entry is customizable
 * enabled / disabled
 * archive file name
 * compression method (tar, targz, zip)
 * store files/directories with/without full path
 * follow symlinks
 * include directories
 * exclude directories
 * exclude filenames
 * exclude filetypes
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

vi ~/.config/backupy/default.cfg
./backupy.py
```


### create custom backup set and start backup ###

```
#!bash

cp ~/.config/backupy/default.cfg /my/path/mybackup.cfg
vi /my/path/mybackup.cfg
./backupy.py /my/path/mybackup.cfg

```

## Contact ##
If you have comments, or just want explain how awesome this scrip is :) - write a mail:

kaktusztea _ at_ protonmail _ dot_ ch