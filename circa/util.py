#!/usr/bin/python

def to_bits_msb(d, bits):
    return [1 if d & (1<<i) else 0 for i in range(bits-1, -1, -1)]

def to_bits_lsb(d, bits):
    return [1 if d & (1<<i) else 0 for i in range(bits)]

def from_bits_lsb(bits):
    return sum((b<<i for i,b in enumerate(bits)))

def from_bits_msb(bits):
    return from_bits_lsb(bits[::-1])

def scale_pulses(pulses, from_clock=1000000, to_clock=38000):
    lt = 0
    lclk = 0
    scaled = []
    for i in pulses:
        t = lt + i
        clk = int(round(t * to_clock / from_clock))
        scaled.append(clk - lclk)
        lclk = clk
        lt = t
    return scaled
