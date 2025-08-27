#!/usr/bin/python
import copy

__all__ = ["CircaError", "ParseError", "DataError", "EncodeError", "DecodeError", "IRCode", "RawCode", "RawPmCode"]

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
        if options:
            for opt in options.split(","):
                try:
                    k, v = opt.split("=", 1)
                except:
                    raise ParseError(f"Could not parse option {opt!r}")
            values[k] = v
        self._set_params(values, short=True)

    @classmethod
    def from_string(cls, typename, code):
        self = cls()
        parts = code.split(":", 1)
        if len(parts) == 1:
            data, = parts
            self._set_params()
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
            raise DataError(f"Format mismatch: {fmt!r} expected one of {self.NAMES!r}")

        data = s.pop("data", None)
        if data is None:
            raise DataError(f"No data in {data!r}")

        self._set_params(s)
        self._set_data(data)

        return self

    @classmethod
    def from_template_and_data(cls, params_string, data):
        self = cls()
        self._set_params_from_string(params_string)
        self._set_data(data)
        return self

    def _clone_from(self, other, data=True):
        if data:
            self.data = copy.deepcopy(other.data)
        else:
            self.data = None
        for lname, sname, validate, default in other.params():
            setattr(self, lname, getattr(other, lname))

    def clone(self, data=True):
        cls = type(self)
        new = cls()
        new._clone_from(self, data)
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
            raise DataError(f"Unknown options: {list(values.keys())!r}")

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

    def to_string_parts(self):
        name = self.NAMES[0]
        params = []
        for lname, sname, validate, default in self.params():
            val = getattr(self, lname)
            if val != default:
                params.append(f"{sname}={val}")
        data = ";".join(self._format_one_string_data(i) for i in self.data)
        return name, ','.join(params), data

    def to_string(self):
        typename, params, data = self.to_string_parts()
        if params:
            return f"{typename}:{params}:{data}"
        else:
            return f"{typename}:{data}"

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
        assert data is not None

        if isinstance(data, list) and isinstance(data[0], int):
            # single string of data
            self.data = [{"pulses": data}]
        else:
            self.data = data
        for packet in self.data:
            for key in packet:
                if key not in ("pulses", "count"):
                    raise DataError(f"Unsupported key: {key!r}")
            if "pulses" not in packet:
                raise DataError(f"IR packet with no pulses: {packet!r}")
            v = packet["pulses"]
            if len(v) % 2 != 0:
                raise DataError(f"IR pulse data length not a multiple of 2: {packet!r}")

    def _parse_string_data(self, data):
        l = [self._parse_one_string_data(i) for i in data.split(";")]
        if len(l) == 1:
            return l[0]
        else:
            return [{"data": i} for i in l]

    def _parse_one_string_data(self, s):
        if s and s[0] == "[" and s[-1] == "]":
            s = s[1:-1]
        d = [abs(int(i.strip())) for i in s.replace(",", " ").split()]
        if len(d) % 2 == 1:
            d.append(1000)
        return d

    def _format_one_string_data(self, d):
        s = ",".join(str(int(i)) for i in d["pulses"])
        if "count" in d and d["count"] != 1:
            s = "%d/" % d["count"] + s
        return s

    @classmethod
    def from_code(cls, code):
        self = cls()
        self._clone_from(code.to_raw())
        return self

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

class RawPmCode(RawCode):
    NAMES = ["rawpm"]

    def _format_one_string_data(self, d):
        s = ",".join(str(int(j * (1 - 2 * (i % 2)))) for i, j in enumerate(d["pulses"]))
        if "count" in d and d["count"] != 1:
            s = "%d/" % d["count"] + s
        return s
