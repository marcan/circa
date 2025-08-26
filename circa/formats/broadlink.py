#!/usr/bin/python

import base64

from ..core import IRCode, DataError, DecodeError
from ..util import scale_pulses

__all__ = ["BroadlinkCode"]

class BroadlinkCode(IRCode):
    NAMES = ["broadlink", "b64"]
    CLOCK = 30453

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        self.fc = 38000
        self.count = 1
        self.packet_interval = 0

    def params(self):
        yield from ()

    def _set_data(self, data):
        if isinstance(data, str) or isinstance(data, bytes):
            data = [data]
        super()._set_data(data)

    def _parse_packet(self, packet):
        if isinstance(packet, bytes):
            packet = base64.b64encode(packet).decode("ascii")
        else:
            try:
                base64.b64decode(packet)
            except:
                raise DataError(f"Invalid base64 data: {packet!r}")
        return packet

    def _parse_one_string_data(self, s):
        try:
            base64.b64decode(s)
        except:
            raise ParseError(f"Invalid base64 data: {s!r}")
        return s

    def parse_code(self, code):
        code = code.to_raw().flatten(no_repeats=False)

        pulses = scale_pulses(code.data[0]["pulses"], 1000000, self.CLOCK)

        if code.count > 256:
            raise DecodeError(f"Broadlink format only supports up to 256 repeats (got: {code.count})")

        packet = []
        for pulse in pulses:
            if pulse < 1:
                raise DecodeError("Pulse length < 1")
            elif pulse > 0xffff:
                raise DecodeError(f"Pulse length too long: {pulse}")
            elif pulse > 255:
                packet += [0, pulse >> 8, pulse & 0xff]
            else:
                packet.append(pulse)

        if len(packet) > 0xffff:
            raise DecodeError(f"Packet is too long: {len(packet)} bytes")

        packet = [0x26, code.count - 1, len(packet) & 0xff, len(packet) >> 8, *packet]

        if len(packet) % 16 != 0:
            packet += bytes(16 - (len(packet) % 16))

        self.data = [base64.b64encode(bytes(packet)).decode("ascii")]

    def _format_one_string_data(self, d):
        return d

    def encode_packet(self, packet, state=None):
        data = base64.b64decode(packet)
        if data[0] != 0x26:
            raise EncodeError(f"Packet header is not 0x26: 0x{data[0]:02x}")

        count = data[1] + 1
        length = data[2] + (data[3] << 8)
        if length > (len(data) - 4):
            raise EncodeError("Packet is too short")

        data = data[4:4+length]

        p = 0
        pulses = []
        while p < length:
            pulse = data[p]
            p += 1
            if pulse == 0:
                pulse = (data[p] << 8) | data[p + 1]
                p += 2
            pulses.append(pulse)

        pulses = scale_pulses(pulses, self.CLOCK, 1000000)

        return count, pulses
