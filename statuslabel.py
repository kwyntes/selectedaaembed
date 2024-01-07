# might make this into a library/package someday
# if i hate myself enough for that...

import os
import re
import sys
import time
from enum import Enum


class tclr(Enum):
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7

    @staticmethod
    def ansi_fg(clr: 'tclr'):
        return f'\x1b[{30 + clr.value}m'

    @staticmethod
    def ansi_bg(clr: 'tclr'):
        return f'\x1b[{40 + clr.value}m'


# https://stackoverflow.com/a/14693789/8649828
ANSI_ESCAPE_RX = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class statuslabel:
    """
    (re)render by calling .status(...)
    """

    def __init__(self, label: str):
        self.label = label

        termsize = os.get_terminal_size()

        self._nlines = 0
        self._linebuf = []
        self._max_lines = termsize.lines - 1
        self._rewrite = False
        self._max_width = termsize.columns

    def status(self, statustext: str, *, bg: tclr = None, invclr=False):
        assert invclr or bg is not None
        ansi_clr = '\x1b[7m' if invclr else tclr.ansi_bg(bg)
        sys.stdout.write(
            # go up min(nlines, max_lines) lines
            '\x1bM' * min(self._nlines, self._max_lines)
            # write the statuslabel
            + f'\r{ansi_clr}{statustext}\x1b[0m {self.label}\x1b[0K'
            # go down min(nlines, max_lines) lines
            + '\n' * min(self._nlines, self._max_lines)
        )

    def __enter__(self):
        return self

    def __exit__(self, _, __, ___):
        # reprint all lines in case it has scrolled
        if self._nlines > self._max_lines:
            sys.stdout.write(
                # go up max_lines - 1 lines
                '\x1bM' * (self._max_lines - 1)
                # write all buffered lines over the existing content
                + '\n'.join(f'{line}\x1b[0K' for line in self._linebuf)
            )
        if self._rewrite:
            # clear the line we're on because it's rewritable
            # so now the next statuslabel or print statement or whatever can
            # reuse the line
            sys.stdout.write('\x1b[2K\r')
        else:
            # print the final newline
            sys.stdout.write('\n')

    def log(self, line: str, rewritable=False):
        # deal with text wrapping in terminals
        # fuck terminals so fucking hard why are still using this 1900s tech
        # today we have browsers that can render ANYTHING you'd ever want
        # fuck this fuck this fuck this i'll write a web interface or
        # something someday idkk
        # oh yeah, rewritable=True lines will just break when they wrap
        # i could theoretically deal with that, but fuck no.
        # this is already such a mess of spaghetti code i don't want to
        # touch it ever again.
        # also yeah im too lazy to import math
        linedelta = max(1, -(len(ANSI_ESCAPE_RX.sub('',
                                                 line)) // -self._max_width))
        if self._rewrite:
            linedelta -= 1
            self._linebuf.pop()
        self._nlines += linedelta
        self._linebuf.append(line)

        # scrolling
        if self._nlines > self._max_lines and linedelta > 0:
            sys.stdout.write(
                # go up max_lines - 1 lines (-1 because we print the newline
                # BEFORE the line instead of after like normally)
                '\x1bM' * (self._max_lines - 1)
                # delete the same amount of lines as we will output
                + f'\x1b[{linedelta}M'
                # go down max_lines - 1 lines, minus linedelta because that many were deleted
                + '\n' * (self._max_lines - 1 - linedelta)
            )

        sys.stdout.write(
            ('\r' if self._rewrite else '\n')
            + f'{line}\x1b[0K'
        )
        self._rewrite = rewritable


# testing
if __name__ == '__main__':
    with statuslabel('Copying files...') as sl:
        sl.status('WORKING', bg=tclr.CYAN)

        n = 200
        for i in range(n):
            sl.log(f'[{i/n*100:>5.1f}%] File {i+1}', rewritable=True)
            time.sleep(0.05)
            sl.log(f'File {i+1} ({"a" * i*2}) copied')

        sl.status('DONE', bg=tclr.GREEN)
