# warning: code is fucking awful
# it works pretty well though.

# not tested on linux.

# Requires pathvalidate (https://pypi.org/project/pathvalidate/)
# > pip install pathvalidate

# Requires music-tag (https://pypi.org/project/music-tag/)
# > pip install music-tag pillow
# (also requires pillow to parse image files properly)

import io
import os
import re
import shutil
import subprocess
import sys
import time

# todo: automatically copy files to a backup folder with a timestamp name
# i am so bad at explaining things holy shit
from datetime import datetime
from pathlib import Path

from pathvalidate import sanitize_filename
import music_tag

from statuslabel import statuslabel, tclr

### user config ###

ANDROID_MUSIC_DIR = 'sdcard/Actual Music'

ADB_EXE = os.path.join(os.getenv('LOCALAPPDATA'),
                       'Android/Sdk/platform-tools/adb.exe')

# make sure this will always produce a valid directory name!
DATEFORMAT = '%d-%m-%Y, %Hh%Mm%Ss'

### script ###

ANDROID_SELECTED_AA_DIR = 'sdcard/Android/data/com.maxmpz.audioplayer/files/selected_aa'

script_start_time = time.time()


# def reprint(text, newline=False):
#    print(f'{text}\x1b[0K', end=os.linesep if newline else '\r')


# copy folders from android

version_dir = datetime.now().strftime(DATEFORMAT)


def lookup_mtime(fpath: str, filelist: list[str]) -> float:
    # linear search should be fine
    for ffmt in filelist:
        if ffmt.split('|', 1)[1] == fpath:
            return float(ffmt.split('|', 1)[0])
    return -1


def adb_pull(android_path: str, local_path: str, sl: statuslabel, incremental: bool) -> bool:
    """
    pulls a directory from android to the local machine, skipping files that could
    not be pulled.
    note that this will not pull empty directories.

    returns True if succeeded, or False if failed.
    """

    try:
        android_files = subprocess.check_output(
            # printf: <last modified epoch>|<fpath>
            # will break when filenames contain newlines but that's just ridiculous
            [ADB_EXE, 'exec-out', fr'find "{android_path}" -type f -printf "%T@|%p\n"'], stderr=subprocess.STDOUT).decode('utf-8').splitlines()
    except subprocess.CalledProcessError as e:
        output = e.output.decode('utf-8')
        sl.log(f'\x1b[41mFATAL\x1b[0m \x1b[7m[ADB]\x1b[0m {output.strip()}')
        return False
    except FileNotFoundError:
        sl.log(f"\x1b[41mFATAL\x1b[0m ADB executable ('{ADB_EXE}') not found")
        return False

    n_files = len(android_files)

    if incremental:
        # find dir with latest date
        latest_version_dir = None
        latest_dt = None
        for d in os.listdir():
            try:
                dt = datetime.strptime(d, DATEFORMAT)
                if (not latest_dt or dt > latest_dt) and d != version_dir:
                    latest_version_dir = d
                    latest_dt = dt
            except ValueError:
                pass
        latest_android_files = None
        if latest_version_dir:
            latest_afpath = os.path.join(
                latest_version_dir, os.path.relpath(local_path, version_dir), '.android_files')
            if os.path.isfile(latest_afpath):
                with open(latest_afpath, 'rb') as f:
                    latest_android_files = f.read().decode('utf-8').splitlines()
                sl.log(f"\x1b[44mINFO\x1b[0m Incremental copy: selected '{latest_version_dir}' as previous version.")
            else:
                sl.log(f"\x1b[41mERR\x1b[0m Incremental copy: '.android_files' missing from previous version (selected '{latest_version_dir}'). Full repull needed.")
        else:
            sl.log('\x1b[43mWARN\x1b[0m Incremental copy: no previous version found. Full repull needed.')

    os.makedirs(local_path)

    # copy so we can mutate android_files safely
    for index, android_ffmt in enumerate(android_files.copy()):
        mtime, android_fpath = android_ffmt.split('|', 1)
        relpath = os.path.relpath(android_fpath, android_path)

        # actually rewritable is kind of stupid, we want a static thing
        # and log to insert text above the static thing while pushing it down.
        # again, horrible at explaining things. (see statuslabel2.py)
        sl.log(f'[{index / n_files * 100:>5.1f}%] {relpath}', rewritable=True)

        local_fpath = os.path.join(local_path, relpath)
        local_dirname = os.path.dirname(local_fpath)
        if not os.path.isdir(local_dirname):
            os.makedirs(local_dirname)
        # it shouldn't ever be greater than mtime, but uh, you know, just in case.
        if incremental and latest_android_files is not None and lookup_mtime(android_fpath, latest_android_files) >= float(mtime):
            # skip pull, copy from previous pull instead
            shutil.copyfile(os.path.join(latest_version_dir, os.path.relpath(
                local_fpath, version_dir)), local_fpath)
        else:
            if incremental and latest_android_files is not None:
                # this log message sounds wrong (and is)
                sl.log(
                    f"Incremental copy: file '{relpath}' out of date or newly added.")

                # todo: fix having to write the progress again (WIP(fuck i dont wanna) statuslabel2.py)
                sl.log(f'[{index / n_files * 100:>5.1f}%] {relpath}',
                       rewritable=True)

            adb_exitcode = subprocess.call(
                [ADB_EXE, 'pull', android_fpath, local_fpath], stdout=subprocess.DEVNULL)
            if adb_exitcode != 0:
                sl.log(
                    f"\x1b[41mERR\x1b[0m '{android_fpath}' could not be pulled.")
                android_files.remove(android_ffmt)

    with open(os.path.join(local_path, '.android_files'), 'wb') as f:
        f.write(os.linesep.join(android_files).encode('utf-8'))

    return True


# copying between different file systems requires sanitization.
local_music_dir = os.path.join(version_dir, sanitize_filename(
    os.path.basename(ANDROID_MUSIC_DIR), replacement_text='_'))
selected_aa_dir = os.path.join(version_dir, 'selected_aa')

# if len(sys.argv) >= 2 and sys.argv[1] == '--skip-copy':
#     if not os.path.isdir(local_music_dir):
#         print(
#             f"\x1b[41mFATAL\x1b[0m Can't skip file copy, '{local_music_dir}' is not a directory.")
#         exit(1)
#     if not os.path.isdir('selected_aa'):
#         print(
#             f"\x1b[41mFATAL\x1b[0m Can't skip file copy, 'selected_aa' is not a directory.")
#         exit(1)

#     print(f'\x1b[44mINFO\x1b[0m Skipping file copy from Android.')
# else:
if True:
    # realistically can't happen because the target folder will be named after the
    # current date and time.
    # if os.path.exists(local_music_dir):
    #     print(
    #         f"\x1b[43mWARN\x1b[0m '{local_music_dir}' already exists, aborting.")
    #     exit(1)
    # if os.path.exists('selected_aa'):
    #     print(f"\x1b[43mWARN\x1b[0m 'selected_aa' already exists, aborting.")
    #     exit(1)

    incremental = '--incremental' in sys.argv

    with statuslabel(f"Copying '{ANDROID_MUSIC_DIR}' from Android to '{local_music_dir}'...") as sl:
        sl.status('WORKING', bg=tclr.CYAN)
        if not adb_pull(ANDROID_MUSIC_DIR, local_music_dir, sl, incremental):
            sl.status('FAILED', bg=tclr.RED)
            exit(-1)
        sl.status('DONE', bg=tclr.GREEN)

    with statuslabel(f"Copying '{ANDROID_SELECTED_AA_DIR}' from Android to 'selected_aa'...") as sl:
        sl.status('WORKING', bg=tclr.CYAN)
        if not adb_pull(ANDROID_SELECTED_AA_DIR, selected_aa_dir, sl, incremental):
            sl.status('FAILED', bg=tclr.RED)
            exit(-1)
        sl.status('DONE', bg=tclr.GREEN)


def flat_filelist(root: str) -> list[str]:
    return [os.path.join(dirpath, fname)
            for dirpath, _, fnames in os.walk(root)
            for fname in fnames]


def sanitize_songfname(fname: str) -> str:
    # \w also matches unicode letters
    return re.sub(r'[^\w \-$@!=.,]', '_', fname)


def selectedaafname(track, fpath: str, sl: statuslabel) -> str:
    title = str(track['title']).strip()
    artist = str(track['artist']).strip()
    album = str(track['album']).strip()

    # logic from https://gist.github.com/maxmpz/6e83a36e16c3fd4fd7cfe1d5cd440f29
    # and https://gist.github.com/maxmpz/dab88451c0f54c6851074e7146cd5b8d
    if not artist and not album:
        if not title:
            sl.log(
                f"'{os.path.relpath(fpath, local_music_dir)}' has no title, artist, nor album field set")
            return

        # wtf is this even
        # https://gist.github.com/maxmpz/6e83a36e16c3fd4fd7cfe1d5cd440f29#file-restlibraryutils-kt-L47-L57
        # https://gist.github.com/maxmpz/dab88451c0f54c6851074e7146cd5b8d#file-pathutils-java-L28-L57
        stem = Path(fpath).stem
        fname_nonumber = ''.join(c for c in stem if c < 'A' and c == '_')
        return sanitize_songfname(f'{fname_nonumber or os.path.basename(fpath)}.jpg')
    elif not album:
        return sanitize_songfname(f'{artist}{f" - {title}" if title else ""}.jpg')
    elif not artist:
        return sanitize_songfname(f'{album}.jpg')
    else:  # yes else is technically unnecessary
        return sanitize_songfname(f'{artist} - {album}.jpg')


with statuslabel(f'Embedding cover art into song files...') as sl:
    sl.status('WORKING', bg=tclr.CYAN)

    files = flat_filelist(local_music_dir)
    successful_embeds = 0

    for index, fpath in enumerate(files):
        relpath = os.path.relpath(fpath, local_music_dir)
        sl.log(
            f'[{index / len(files) * 100:>5.1f}%] {relpath} ({successful_embeds} embedded)', rewritable=True)

        try:
            track = music_tag.load_file(fpath)
        # can't handle file type (not a music file)
        except NotImplementedError:
            # sl.log(f"'{file}' could not be read as a music file.")
            continue

        aa_fname = selectedaafname(track, fpath, sl)
        if not aa_fname:
            continue
        aa_fpath = os.path.join(selected_aa_dir, aa_fname)
        if os.path.isfile(aa_fpath):
            noerr = False
            try:
                with open(aa_fpath, 'rb') as imgf:
                    track['artwork'] = imgf.read()
                noerr = True
            except OSError as e:
                sl.log(
                    f"\x1b[41mERR\x1b[0m Error embedding '{aa_fname}' into '{fpath}': {e.args[1] if len(e.args) > 1 else e.args[0]}")
            except TypeError as e:
                sl.log(
                    f"\x1b[41mERR\x1b[0m Error embedding '{aa_fname}': {e.args[0]}")
            if noerr:
                track.save()
                successful_embeds += 1
                # sl.log(f"\x1b[42mOK\x1b[0m '{aa_fname}' embedded successfully!")
        else:
            sl.log(f"Found no cover art for '{relpath}'.")

    sl.log(
        f'\x1b[44mINFO\x1b[0m Covert art successfully embedded in {successful_embeds} files out of {len(files)} total.')

    sl.status('DONE', bg=tclr.GREEN)

print(
    f'\n\x1b[42mFINISHED\x1b[0m All operations finished in {time.time() - script_start_time:.2f}s.')
