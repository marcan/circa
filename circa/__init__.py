#!/usr/bin/python

from .core import *
from .formats.nec import NECCode
from .formats.rc5 import RC5Code
from .formats.broadlink import BroadlinkCode
from .devices.broadlink import BroadlinkDevice

FORMATS = [
    RawCode,
    RC5Code,
    NECCode,
    BroadlinkCode,
]

DEVICES = [
    BroadlinkDevice
]

def find_format(fmtname):
    for fmt in FORMATS:
        if fmtname in fmt.NAMES:
            return fmt
    raise ParseError("Format type %s not supported" % fmtname)

def find_device(devname):
    for dev in DEVICES:
        if devname in dev.NAMES:
            return dev
    raise ParseError("Device type %s not supported" % devname)

def from_string(s):
    fmtname, data = s.split(":", 1)
    fmt = find_format(fmtname)
    return fmt.from_string(fmtname, data)

def from_struct(s):
    if "format" not in s:
        raise DataError("No format defined")
    fmtname = s["format"]
    for fmt in FORMATS:
        if fmtname in fmt.NAMES:
            return fmt.from_struct(s)
    raise ParseError("Format type %s not supported" % fmtname)

def compare_codes(a, b):
    a = a.to_raw().flatten().data[0]["pulses"]
    b = b.to_raw().flatten().data[0]["pulses"]

    worst = 0
    median = sorted(a)[len(a) // 2]
    for i, j in zip(a[:-1], b[:-1]):
        diff = abs(j - i) / i
        diff = diff * (min((median / i), 1) ** 0.1)
        worst = max(diff, worst)

    score = 1.0 - min(worst, 1.0)

    length_diff = abs(len(a) - len(b))

    score *= 0.8 ** max(0, (length_diff - 1))
    return score

def try_decode(code):
    raw = code.to_raw().flatten()

    guesses = []

    for fmt in FORMATS:
        try:
            ncode = fmt.from_code(code)
        except:
            continue
        guesses.append((compare_codes(raw, ncode), ncode))

        best_scode = None
        for threshold in (0.05, 0.1, 0.15, 0.2, 0.25):
            scode = ncode.clone()
            scode.simplify_params(threshold)
            score =compare_codes(raw, scode)
            if score < 0.7:
                break
            best_scode = score, scode
            if guesses and guesses[-1][0] == score:
                guesses.pop()
            guesses.append(best_scode)

    guesses.sort(reverse=True, key=lambda k: k[0])
    return guesses
