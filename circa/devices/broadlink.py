#!/usr/bin/python
import time, base64

try:
    import broadlink
    from broadlink.exceptions import ReadError, StorageError
except ImportError:
    broadlink = None

from ..core import *
from ..formats.broadlink import BroadlinkCode

__all__ = ["BroadlinkDevice"]

class BroadlinkDevice(object):
    NAMES = ["broadlink"]
    def __init__(self, args):
        if not broadlink:
            raise Exception("broadlink module not available")
        devtype, host, mac = args.split(":")
        devtype = int(devtype, 0)
        mac = bytearray.fromhex(mac)

        self.dev = broadlink.gendevice(devtype, (host, 80), mac)
        self.dev.auth()

    def receive(self):
        self.dev.enter_learning()
        TIMEOUT = 60
        start = time.time()
        while time.time() - start < TIMEOUT:
            time.sleep(1)
            try:
                data = self.dev.check_data()
            except (ReadError, StorageError):
                continue
            code = BroadlinkCode(data).to_raw()
            # The first pulse usually ends up short by about this much
            code.data[0]["pulses"][0] += 128
            return code
        return None

    def transmit(self, code):
        if not isinstance(code, BroadlinkCode):
            data = BroadlinkCode.from_code(code)
        for packet in data.data:
            self.dev.send_data(base64.b64decode(packet))
