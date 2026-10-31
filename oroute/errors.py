"""What is wrong with the input of a script, said in one line a caller can read.

A script that cannot go on because of what it was given (a recording without GPS, a map with no course
printed on it) ends with exit code 2 and the line

    OB-ERROR <code>: <what is wrong, in English>

instead of a traceback. The web app turns the code into a Czech sentence (webapp/texts.py: analysis_error);
anything else a script dies of is a bug and keeps its traceback.
"""
import re
import sys

MARK = "OB-ERROR"
CODES = (
    "bad_fit",            # the file is no .fit activity that can be read
    "no_gps",             # the recording has no GPS position at all
    "no_course_print",    # the map "with the course" has no purple course on it
    "no_start",           # control circles were read, the start triangle was not
    "no_finish",          # ... the finish (double circle) was not
    "track_off_course",   # the track does not come near the controls: another run, or it does not cover the race
)


class InputError(Exception):
    """The input cannot be analysed: code (one of CODES) and what is wrong, in English."""

    def __init__(self, code, text):
        assert code in CODES, code
        super().__init__(f"{code}: {text}")
        self.code, self.text = code, text


def run(main):
    """Run the main() of a script; an InputError ends it with the OB-ERROR line and exit code 2."""
    try:
        main()
    except InputError as e:
        print(f"{MARK} {e.code}: {e.text}", flush=True)
        sys.exit(2)


def parse(lines):
    """(code, text) of the last OB-ERROR line among the lines a script printed, or None."""
    for line in reversed(list(lines)):
        m = re.match(rf"{MARK} (\w+): (.*)", line.strip())
        if m:
            return m.group(1), m.group(2)
    return None
