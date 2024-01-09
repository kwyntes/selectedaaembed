# selectedaaembed

Python script to automatically embed cover art from Poweramp's internal
selected_aa folder into music files.

Not tested on Linux, although it _should_ work if you point `ADB_EXE` to the
right path for the ADB executable.

## How to use

Modify the `ANDROID_MUSIC_DIR` and `ADB_EXE` to point to the right places, then execute

```
> python3 selectedaaembed.py [--incremental]
```

and that's it. The script will copy the chosen music folder and the selected_aa
folder from your phone to this computer, and try to embed all chosen album art
into the files.

~~You can use `--skip-copy` to run the script without copying anything from your
phone. I added this for debugging purposes, but it might be useful in case
you've already got the files copied from your phone previously, or don't have
ADB installed and want to copy the files manually.~~

### Prerequisites

- Requires pathvalidate (https://pypi.org/project/pathvalidate/)  
  `> pip install pathvalidate`

- Requires music-tag (https://pypi.org/project/music-tag/)  
  `> pip install music-tag pillow`  
  (also requires pillow to parse image files properly, on Windows at least)

### TODO

- [ ] Optionally rename music files as well;
- [x] Copy files into a folder labelled with a date/timestamp for versioning;
- [x] Incremental copy.
  > because this program also modifies the files, we will need to store the
  > timestamps from android in a seperate file (.android_files)

~~**Note: because incremental copy uses a seperate file to store what files have
been pulled previously, it will not be able to recover from any errors or manual
termination.**~~
sort of fixed by removing files that failed to be pulled from the list and only
writing the list to a file *after* all the full procedure has finished.