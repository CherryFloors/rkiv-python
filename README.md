# rkiv-python
Helps organize and archive optical media

# Notes
#### Damaged Discs

If discs are damaged, `ddrescue` might help.

Install
```sh
sudo apt install gddrescue
```

First Pass
```sh
ddrescue -b 2048 -n -v /dev/sr0 dvd.iso rescue.log
```

Second Pass
```sh
ddrescue -b 2048 -d -r 3 -v /dev/sr0 dvd.iso rescue.log
```

Third Pass
```sh
ddrescue -b 2048 -d -R -r 3 -v /dev/sr0 dvd.iso rescue.log
```

## ARM Todo
- finish logging and notification parsing
- print notifications on exit
- add option to do old school disc backup/abort if discs are too big

