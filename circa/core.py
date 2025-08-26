#!/usr/bin/python
import copy

__all__ = ["CircaError", "ParseError", "DataError", "EncodeError", "DecodeError", "IRCode", "RawCode"]

class CircaError(Exception):
    pass

class ParseError(CircaError):
    pass

class DataError(CircaError):
    pass

class EncodeError(CircaError):
    pass

class DecodeError(CircaError):
    pass

class IRCode(object):
    def __init__(self, data=None, **kwargs):
        self._set_params(kwargs)
        if data is None:
            self.data = None
        else:
            self._set_data(data)

    def _set_params_from_string(self, options):
        values = {}
        for opt in options.split(","):
            try:
                k, v = opt.split("=", 1)
            except:
                raise ParseError("Could not parse option %r" % opt)
            values[k] = v
        self._set_params(values, short=True)

    @classmethod
    def from_string(cls, typename, code):
        self = cls()
        parts = code.split(":", 1)
        if len(parts) == 1:
            params, = parts
            self._set_params_from_string(options)
        else:
            options, data = parts
            self._set_params_from_string(options)

        if data:
            self._set_data(self._parse_string_data(data))
        else:
            self.data = None
        return self

    @classmethod
    def from_code(cls, code):
        if type(code) == cls:
            return code.clone()
        obj = cls()
        obj.parse_code(code)
        return obj

    @classmethod
    def parse_code(cls, code):
        raise NotImplementedError()

    @classmethod
    def from_struct(cls, struct):
        self = cls()
        s = dict(struct)
        fmt = s.pop("format", None)
        if fmt is not None and fmt not in self.NAMES:
            raise DataError("Format mismatch: %r expected one of %r" % (fmt, self.NAMES))

        data = s.pop("data", None)
        if data is None:
            raise DataError("No data in %r" % data)

        self._set_params(s)
        self._set_data(data)

        return self

    def clone(self, data=True):
        cls = type(self)
        new = cls()
        if data:
            new.data = copy.deepcopy(self.data)
        else:
            new.data = None
        for lname, sname, validate, default in self.params():
            setattr(new, lname, getattr(self, lname))
        return new

    def _parse_string_data(self, data):
        return [self._parse_one_string_data(i) for i in data.split(";")]

    def _parse_one_string_data(self, s):
        raise NotImplementedError()

    def _set_params(self, values={}, short=False):
        values = dict(values)
        for lname, sname, validate, default in self.params():
            name = sname if short else lname
            setattr(self, lname, validate(values.pop(name, default)))

        if values:
            raise DataError("Unknown options: %r" % list(values.keys()))

    def _set_data(self, data):
        self.data = [self._parse_packet(packet) for packet in data]

    def _format_packet(self, packet):
        pass

    def params(self):
        yield ("fc", "f", int, 38000)
        yield ("count", "c", int, 1)
        yield ("packet_interval", "pi", int, 0)

    def to_raw(self, state=None):
        raw_data = []
        for packet in self.data:
            count, pulses = self.encode_packet(packet, state)
            if self.count > 1 or len(self.data) > 1:
                pulses[-1] += max(0, self.packet_interval - sum(pulses))
            raw_data.append({"count": count, "pulses": pulses})
        raw = RawCode(raw_data, fc=self.fc, count=self.count)
        return raw

    def encode_packet(self, packet, state=None):
        raise NotImplementedError()

    def to_string(self):
        name = self.NAMES[0]
        params = []
        for lname, sname, validate, default in self.params():
            val = getattr(self, lname)
            if val != default:
                params.append("%s=%s" % (sname, val))
        data = ";".join(self._format_one_string_data(i) for i in self.data)
        if params:
            return "%s:%s:%s" % (name, ",".join(params), data)
        else:
            return "%s::%s" % (name, data)

    def to_struct(self, full=False):
        struct = {"format": self.NAMES[0]}
        for lname, sname, validate, default in self.params():
            val = getattr(self, lname)
            if val != default or full:
                struct[lname] = val
        struct["data"] = self.data
        return struct

    def _reset_samples(self):
        self._samples = {}

    def _sample(self, k, v):
        samples = self._samples.setdefault(k, [])
        samples.append(v)
        setattr(self, k, int(round(sum(samples) / len(samples))))

    def _sample_default(self, k, v):
        if k not in self._samples:
            setattr(self, k, v)

    def simplify_params(self, tolerance=0.2):
        for lname, sname, validate, default in self.params():
            val = getattr(self, lname)
            if default * (1 - tolerance) <= val <= default * (1 + tolerance):
                setattr(self, lname, default)

    def __str__(self):
        return self.to_string()

class RawCode(IRCode):
    NAMES = ["raw"]

    def _set_data(self, data):
        if data is None:
            self.data = None
        elif isinstance(data, list) and isinstance(data[0], int):
            # single string of data
            self.data = [{"pulses": data}]
        else:
            self.data = data
        for packet in self.data:
            for key in packet:
                if key not in ("pulses", "count"):
                    raise DataError("Unsupported key: %r" % key)
            if "pulses" not in packet:
                raise DataError("IR packet with no pulses: %r" % packet)
            v = packet["pulses"]
            if len(v) % 2 != 0:
                raise DataError("IR pulse data length not a multiple of 2" % packet)

    def _parse_string_data(self, data):
        l = [self._parse_one_string_data(i) for i in data.split(";")]
        if len(l) == 1:
            return l[0]
        else:
            return [{"data": i} for i in l]

    def _parse_one_string_data(self, s):
        return [int(i) for i in s.split(",")]

    def _format_one_string_data(self, d):
        s = ",".join(str(int(i)) for i in d["pulses"])
        if "count" in d and d["count"] != 1:
            s = "%d/" % d["count"] + s
        return s

    @classmethod
    def from_code(cls, code):
        return code.to_raw()

    def to_raw(self, state=None):
        return self

    def flatten(self, no_repeats=True):
        if len(self.data) == 1:
            flat = self.clone(data=True)
            if "count" in flat.data[0]:
                flat.count *= flat.data[0]["count"]
                del flat.data[0]["count"]
        else:
            flat = self.clone(data=False)
            pulses = []
            for i in self.data:
                count = i.get("count", 1)
                pulses += count * i["pulses"]
            flat.data = [{"pulses": pulses}]

        length = sum(flat.data[0]["pulses"])
        if flat.count > 1 and length < flat.packet_interval:
            flat.data[0]["pulses"][-1] += flat.packet_interval - length

        if no_repeats and flat.count > 1:
            flat.data[0]["pulses"] *= flat.count
            flat.count = 1

        flat.packet_interval = 0

        return flat
