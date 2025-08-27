#!/usr/bin/python

import base64

from ..core import *
from ..util import scale_pulses

__all__ = ["ProntoCode"]

class ProntoCode(IRCode):
    NAMES = ["pronto"]
    # https://www.majority.nl/files/prontoirformats.pdf
    # Clock is claimed as 4.1455 ± 0.0006 Mhz
    # The original Pronto models had serial ports. This is
    # likely to be 16.5888 MHz (a common UART clock) / 4,
    # which is 4.1472 MHz. Slightly off, but let's go with that.
    CLOCK = 4147200

    def __init__(self, data=None, **kwargs):
        super().__init__(data, **kwargs)
        self.fc = None
        self.count = 1
        self.packet_interval = 0

    def params(self):
        yield from ()

    def clone(self, data=True):
        new = super().clone(data)
        new.fc = self.fc
        return new

    def _set_data(self, data):
        if isinstance(data, str):
            data = [data]

        super()._set_data(data)
        self.fc = self.CLOCK / int(data[0].split()[1], 16)

    def _parse_packet(self, packet):
        try:
            self.encode_packet(packet)
        except:
            raise DataError(f"Invalid Pronto packet: {packet!r}")
        return packet

    _parse_one_string_data = _parse_packet

    def parse_code(self, code):
        base = int(round(self.CLOCK / code.fc))
        self.fc = self.CLOCK / base

        data = [0, base]

        code = code.to_raw().flatten(no_repeats=True)

        pulses = scale_pulses(code.data[0]["pulses"], 1000000, self.fc)

        if len(pulses) % 2:
            raise DecodeError("Odd pulse count")

        if len(pulses) > (0xffff * 2):
            raise DecodeError(f"Packet is too long: {len(pulses)//2} pulses")

        data.append(len(pulses) // 2)
        # TODO: Do something useful for repeat codes
        data.append(0)

        for pulse in pulses:
            if pulse < 1:
                raise DecodeError("Pulse length < 1")
            elif pulse > 0xffff:
                raise DecodeError(f"Pulse length too long: {pulse}")

            data.append(pulse)

        self.data = [" ".join(f"{c:04X}" for c in data)]

    def _format_one_string_data(self, d):
        return d

    def encode_packet(self, packet, state=None):
        data = [int(c, 16) for c in packet.split()]

        if data[0] != 0:
            raise EncodeError(f"Packet header is not 0: 0x{data[0]:02x}")

        base = data[1]
        length = data[2]
        # TODO: Do something useful for repeat codes
        repeat_length = data[3]

        if (2 * length + 2 * repeat_length + 4) != len(data):
            raise EncodeError("Mismatched packet length")

        fc = self.CLOCK / base

        pulses = data[4:4 + length * 2]

        pulses = scale_pulses(pulses, fc, 1000000)

        return 1, pulses
