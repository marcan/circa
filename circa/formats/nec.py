#!/usr/bin/python

import statistics

from ..core import IRCode, DataError, DecodeError
from ..util import to_bits_lsb, from_bits_lsb

__all__ = ["NECCode"]

class NECCode(IRCode):
    NAMES = ["nec"]

    def params(self):
        yield from (i for i in super().params() if i[0] not in "packet_interval")
        yield ("pulse_time", "tp", int, 563)
        yield ("space_time_0", "t0", int, self.pulse_time)
        yield ("space_time_1", "t1", int, self.pulse_time * 3)
        yield ("preamble_time_high", "ph", int, self.pulse_time * 16)
        yield ("preamble_time_low", "pl", int, self.preamble_time_high // 2)
        yield ("repeat_time_high", "rh", int, self.preamble_time_high)
        yield ("repeat_time_low", "rl", int, self.preamble_time_low // 2)
        yield ("address_bytes", "a", int, 0)
        yield ("packet_gap", "pg", int, 0)
        yield ("packet_interval", "pi", int, self.pulse_time * 192 if self.packet_gap == 0 else 0)
        yield ("repeat_interval", "ri", int, self.packet_interval)
        yield ("burst_count", "b", int, 0)
        yield ("burst_time_high", "bh", int, self.pulse_time)
        yield ("burst_time_low", "bl", int, self.pulse_time)
        yield ("burst_gap", "bg", int, self.pulse_time * 60)

    def _parse_packet(self, packet):
        for i in packet:
            if not isinstance(i, int) or not 0 <= i <= 255:
                raise DataError("Invalid data byte: %r" % i)
        return packet

    def _parse_one_string_data(self, s):
        return [int(i, 16) for i in s.split(",")]

    def _format_one_string_data(self, d):
        return ",".join("%02x" % i for i in d)

    def encode_packet(self, packet, state=None):
        if self.address_bytes < 0:
            data, payload = packet, []
        else:
            data, payload = packet[:self.address_bytes], packet[self.address_bytes:]

        for i in payload:
            data.append(i)
            data.append(i ^ 0xff)

        pulses = [self.preamble_time_high, self.preamble_time_low]

        for byte in data:
            for bit in to_bits_lsb(byte, 8):
                pulses.append(self.pulse_time)
                if bit:
                    pulses.append(self.space_time_1)
                else:
                    pulses.append(self.space_time_0)

        pulses.append(self.pulse_time)
        pulses.append(max(self.pulse_time, self.packet_gap))
        padding = 0

        return 1, pulses

    def to_raw(self, state=None):
        raw_code = super().to_raw(state)
        raw_code.packet_interval = 0
        if self.burst_count:
            burst = [self.burst_time_high, self.burst_time_low] * self.burst_count
            burst[-1] = self.burst_gap
            raw_code.data.insert(0, ({"count": 1, "pulses": burst}))
        if self.count > 1:
            raw_code.data.append({"count": self.count - 1, "pulses": [
                self.repeat_time_high, self.repeat_time_low, self.pulse_time,
                max(self.pulse_time, self.repeat_interval - self.repeat_time_high - self.repeat_time_low - self.pulse_time)
            ]})
            raw_code.count = 1
        return raw_code

    def parse_code(self, code):
        self.fc = code.fc

        code = code.to_raw().flatten(no_repeats=True)
        pulses = code.data[0]["pulses"]

        self._reset_samples()

        packets = []
        p = 0
        repeats = 0

        # Try to detect an initial burst...
        if len(pulses) >= 4:
            bmin = min(pulses[1:4])
            bmax = max(pulses[:4])
            bavg = sum(pulses[:4]) / 4
            if pulses[0] < bavg * 1.5 and abs(bmin - bavg) / bavg < 0.3 and (bmax - bavg) / bavg < 0.3:
                while p < (len(pulses)-1):
                    bh, bl = pulses[p:p + 2]
                    if bh > 2 * bavg:
                        self._sample("burst_gap", pulses[p - 1])
                        break
                    self._sample("burst_time_high", bh)
                    self.burst_count += 1
                    p += 2
                    if bl > 2 * bavg:
                        self._sample("burst_gap", bl)
                        break
                    self._sample("burst_time_low", bl)

        if len(pulses) <= p:
            raise DataError("No data")

        last_packet_length = None
        while p < (len(pulses)-1):
            packet_start = p
            hh, hl = pulses[p:p + 2]
            p += 2

            bits = []

            if p >= len(pulses):
                # runt end pulse?
                if not packets:
                    raise DataError("No data")
                break

            if packets and not repeats:
                self._sample("packet_gap", pulses[p - 3])

            while p < (len(pulses)-1):
                mark, space = pulses[p:p+2]
                if (bits or packets) and mark > self.pulse_time * 2:
                    break
                p += 2
                self._sample("pulse_time", mark)
                if space < self.pulse_time * 2:
                    bits.append(0)
                    self._sample("space_time_0", space)
                elif space < self.pulse_time * 6:
                    bits.append(1)
                    self._sample("space_time_1", space)
                else:
                    bits.append(0) # end bit?
                    break

            if (len(bits) % 8) != 1:
                raise DataError("Bit count not an even number of bytes")

            if len(bits) > 1:
                self._sample("preamble_time_high", hh)
                self._sample("preamble_time_low", hl)
                if repeats > 0:
                    raise DataError("Data packet after a repeat packet")
                packets.append([from_bits_lsb(bits[i:i+8]) for i in range(0, len(bits) - 1, 8)])
                if last_packet_length:
                    self._sample("packet_interval", last_packet_length)
            else:
                self._sample("repeat_time_high", hh)
                self._sample("repeat_time_low", hl)
                if not packets:
                    raise DataError("Repeat packet with no data packet")
                if repeats > 0:
                    self._sample("repeat_interval", last_packet_length)
                else:
                    self._sample("packet_interval", last_packet_length)
                repeats += 1

            last_packet_length = sum(pulses[packet_start:p])

        # Packet spacing can be specified with either an interval or a gap.
        # Pick whichever one works best.
        if "packet_interval" in self._samples and "packet_gap" in self._samples:
            if len(self._samples["packet_interval"]) > 1 and len(self._samples["packet_gap"]) > 1:
                vi = statistics.variance(self._samples["packet_interval"])
                vg = statistics.variance(self._samples["packet_gap"])
                if vi > vg:
                    del self._samples["packet_interval"]
                else:
                    del self._samples["packet_gap"]
            else:
                # Just two packets, go with gap
                del self._samples["packet_interval"]

        self._sample_default("packet_gap", 0)
        self._sample_default("packet_interval", self.pulse_time * 192 if self.packet_gap == 0 else 0)
        self._sample_default("repeat_interval", self.packet_interval)
        self._sample_default("repeat_time_high", self.preamble_time_high)
        self._sample_default("repeat_time_low", self.preamble_time_low // 2)
        self._sample_default("burst_time_high", self.pulse_time)
        self._sample_default("burst_time_low", self.pulse_time)
        self._sample_default("burst_gap", self.pulse_time * 60)

        self.address_bytes = len(packets[0]) & 1 # if odd number of bytes, at least one address byte is required
        for packet in packets:
            inv = 0
            for b1, b2 in zip(*([iter(packet[::-1])] * 2)):
                if b1 == b2 ^ 0xff:
                    inv += 2
                else:
                    break
            ab = len(packet) - inv
            if (ab ^ self.address_bytes) & 1: # if the length parity is off, bail
                self.address_bytes = -1
                break
            self.address_bytes = max(ab, self.address_bytes)

        for packet in packets:
            if len(packet) <= self.address_bytes:
                self.address_bytes = -1
                break

        if self.address_bytes != -1:
            packets = [packet[:self.address_bytes] + packet[self.address_bytes::2] for packet in packets]

        self.data = packets
        self.count = repeats + 1
