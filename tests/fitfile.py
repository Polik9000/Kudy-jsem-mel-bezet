"""Write a small valid .fit activity for tests (file_id, records, a session), as a Garmin watch would."""
import datetime as dt
import struct

FIT_EPOCH = dt.datetime(1989, 12, 31, tzinfo=dt.timezone.utc)
SEMI = 2**31 / 180.0
NO_POS = 0x7FFFFFFF      # the invalid value of a position: the watch had no fix
_CRC = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]


def _crc(data, crc=0):
    for b in data:
        for nibble in (b & 0xF, b >> 4):
            tmp = _CRC[crc & 0xF]
            crc = ((crc >> 4) & 0x0FFF) ^ tmp ^ _CRC[nibble]
    return crc


def _definition(local, number, fields):
    """fields: [(field number, size, base type)]"""
    return struct.pack("<BBBHB", 0x40 | local, 0, 0, number, len(fields)) + b"".join(struct.pack("BBB", *f) for f in fields)


def fit_bytes(points, start=dt.datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt.timezone.utc), sport=1):
    """points: [(seconds from the start, lat, lon)]; lat None = a record without a position."""
    t0 = int((start - FIT_EPOCH).total_seconds())
    body = _definition(0, 0, [(0, 1, 0x00)]) + struct.pack("<BB", 0, 4)                 # file_id: type activity
    body += _definition(1, 20, [(253, 4, 0x86), (0, 4, 0x85), (1, 4, 0x85)])            # record: time, lat, lon
    for t, lat, lon in points:
        la, lo = (NO_POS, NO_POS) if lat is None else (int(round(lat * SEMI)), int(round(lon * SEMI)))
        body += struct.pack("<BIii", 1, t0 + int(t), la, lo)
    last = points[-1][0] if points else 0
    body += _definition(2, 18, [(2, 4, 0x86), (5, 1, 0x00), (6, 1, 0x00), (7, 4, 0x86), (8, 4, 0x86), (9, 4, 0x86)])
    body += struct.pack("<BIBBIII", 2, t0, sport, 0, int(last * 1000), int(last * 1000), 0)   # session
    head = struct.pack("<BBHI4s", 14, 0x20, 2100, len(body), b".FIT")
    head += struct.pack("<H", _crc(head))
    return head + body + struct.pack("<H", _crc(head + body))


def write_fit(path, points, **kw):
    with open(path, "wb") as f:
        f.write(fit_bytes(points, **kw))
    return str(path)
