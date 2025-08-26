#!/usr/bin/python

from ..core import IRCode, DataError
from ..util import to_bits_msb, from_bits_msb

__all__ = ["RC5Code"]

class RC5Code(IRCode):
    NAMES = ["rc5"]

    def params(self):
        yield from (i for i in super().params() if i[0] not in "packet_interval")
        yield ("packet_interval", "ri", int, 113788)
        yield ("bit_time", "tb", int, 889)

    def _parse_packet(self, packet):
        if isinstance(packet, list) or isinstance(packet, tuple):
            addr, cmd = map(int, packet)
        elif isinstance(packet, dict):
            if set(packet.keys()) != set(("addr", "cmd")):
                raise DataError(f"Unsupported packet keys: {list(packet.keys())!r} (expected addr, cmd)")
            try:
                addr, cmd = int(packet["addr"]), int(packet["cmd"])
            except:
                raise DataError(f"Invalid packet data {packet!r}")
        if not 0 <= addr <= 31:
            raise DataError(f"Address {addr} not in [0..31]")
        if not 0 <= cmd <= 127:
            raise DataError(f"Command {cmd} not in [0..127]")
        return {"addr": addr, "cmd": cmd}

    def _parse_one_string_data(self, s):
        addr, cmd = s.split(",")
        return {"addr": int(addr, 0), "cmd": int(cmd, 0)}

    def _format_one_string_data(self, d):
        return "%d,%d" % (d["addr"], d["cmd"])

    def encode_packet(self, packet, state=None):
        addr, cmd = packet["addr"], packet["cmd"]

        toggle = 1

        if state is not None:
            key = f"rc5-toggle-{addr}-{cmd}"
            toggle = state.get(key, 1)

        toggle ^= 1

        bits = [0 if (cmd & 0x40) else 1, toggle, *to_bits_msb(addr, 5), *to_bits_msb(cmd & 0x3f, 6)]

        pulses = [self.bit_time]
        last = 1
        for b in bits:
            if b == last:
                pulses += [self.bit_time, self.bit_time]
            else:
                pulses[-1] += self.bit_time
                pulses.append(self.bit_time)
            last = b

        if last == 1:
            pulses.append(self.bit_time)

        if state is not None:
            state[key] = toggle

        return 1, pulses

    def parse_code(self, code):
        self.fc = code.fc

        code = code.to_raw().flatten(no_repeats=True)
        pulses = list(code.data[0]["pulses"])

        self._reset_samples()

        packets = []
        p = 0

        if not len(pulses):
            raise DataError("No data")

        # RC5 has no sane framing, so we need to guess
        max_mark = max(pulses[::2])

        # a space longer than 4 of the longest marks means a new packet
        pause = max_mark * 4

        packet_start = 0
        last_packet_length = None
        while p < (len(pulses)-1):
            packet_start = p

            times = []
            while p < (len(pulses)-1):
                mark, space = pulses[p:p + 2]
                p += 2
                if space > pause:
                    break



            times = pulses[packet_start:p - 1]
            times.sort()

            if len(times) < 13:
                raise DataError("Packet too short")
            if len(times) > 29:
                raise DataError("Packet too long")

            # Ignore the shortest pulse and longest pulse, in case of noise
            min_time = min(times[1:])
            max_time = max(times[:-1])

            # If there isn't enough difference between the pulse times, we might have a special
            # case of 10101010101010 or 11111111111111 or off by one bit
            th = (min_time + max_time) / 2
            if (max_time / min_time) < 1.3:
                if len(times) <= 15:
                    th = th * 0.75
                elif len(times) >= 25:
                    th = th * 1.5

            bits = [1]
            skip = False
            for t in pulses[packet_start:p - 1]:
                if t > th:
                    if skip:
                        raise DataError("Invalid Manchester encoding")
                    self._sample("bit_time", t / 2)
                    bits.append(bits[-1] ^ 1)
                else:
                    self._sample("bit_time", t)
                    if skip:
                        skip = False
                    else:
                        bits.append(bits[-1])
                        skip = True

            # Allow some garbage at the end
            if not 14 <= len(bits) <= 16:
                raise DataError(f"Packet length invalid: {len(bits)}")

            bits = bits[:14]
            toggle = bits[2]
            addr = from_bits_msb(bits[3:8])
            cmd = from_bits_msb([1 ^ bits[1]] + bits[8:14])
            packets.append((toggle, addr, cmd))

            if last_packet_length:
                self._sample("packet_interval", last_packet_length)
            last_packet_length = sum(pulses[packet_start:p])

        if all(i == packets[0] for i in packets[1:]):
            self.count = len(packets)
            packets = [packets[0]]

        self.data = [{"addr": addr, "cmd": cmd} for toggle, addr, cmd in packets]
