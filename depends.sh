#!/bin/bash

## libcdio
apt-get install swig
apt-get install libcdio-dev
apt-get install libiso9660-dev
# dvd/bluray/mkv
apt-get install dvdbackup
apt-get install libdvd-pkg && dpkg-reconfigure libdvd-pkg
apt-get install mkvtoolnix-gui
apt-get install ccextractor
apt-get install handbrake
# cd
apt-get install abcde lame eyed3 glyrc cdparanoia flac atomicparsley
apt-get install dvd+rw-tools