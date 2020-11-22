#!/usr/bin/python
import argparse, itertools

from . import from_string, try_decode, find_format, find_device

def do_convert(args):
    code = from_string(args.code)
    target = find_format(args.format)
    converted = target.from_code(code)
    if args.threshold is not None:
        converted.simplify_params(args.threshold)
    print(converted.to_string())

def do_simplify(args):
    code = from_string(args.code)
    code.simplify_params(args.threshold)
    print(code.to_string())

def do_decode(args):
    code = from_string(args.code)
    for score, guess in try_decode(code):
        print("%.01f%% %s" % (score * 100, guess))

def do_transmit(args):
    code = from_string(args.code)
    devtype, params = args.device.split(":", 1)
    dev = find_device(devtype)(params)
    dev.transmit(code)

def do_receive(args):
    devtype, params = args.device.split(":", 1)
    dev = find_device(devtype)(params)
    if args.count == 0:
        it = itertools.count(start=1)
    else:
        it = range(args.count)
    for i in it:
        code = dev.receive()
        print("=== Received code ===")
        for score, guess in try_decode(code):
            print("%.01f%% %s" % (score * 100, guess))

def main():
    parser = argparse.ArgumentParser(prog="PROG", description='IR code multitool')

    subparsers = parser.add_subparsers(help='sub-command help', dest="cmd")
    subparsers.required = True

    p_convert = subparsers.add_parser('convert', description="Convert a code to another format")
    p_convert.add_argument('-f', "--format", metavar="FORMAT", type=str, default="raw", help="target format")
    p_convert.add_argument('-t', "--threshold", type=float, default=None, metavar="THRESHOLD", help="also simplify")
    p_convert.add_argument('code', metavar='TYPE:CODE', type=str, help='IR code to convert')
    p_convert.set_defaults(func=do_convert)

    p_simplify = subparsers.add_parser('simplify', description="Remove redundant parameters")
    p_simplify.add_argument('-t', "--threshold", type=float, default=0.2, metavar="THRESHOLD", help="threshold for matching against defaults")
    p_simplify.add_argument('code', metavar='TYPE:CODE', type=str, help='IR code to simplify')
    p_simplify.set_defaults(func=do_simplify)

    p_decode = subparsers.add_parser('decode', description="Automatically attempt to decode an IR code")
    p_decode.add_argument('code', metavar='TYPE:CODE', type=str, help='IR code to decode')
    p_decode.set_defaults(func=do_decode)

    p_transmit = subparsers.add_parser('transmit', description="Transmit an IR code with a blaster")
    p_transmit.add_argument('device', metavar='TYPE:ARGS', type=str, help='Target device type/info')
    p_transmit.add_argument('code', metavar='TYPE:CODE', type=str, help='IR code to decode')
    p_transmit.set_defaults(func=do_transmit)

    p_receive = subparsers.add_parser('receive', description="Receive and decode an IR code with a blaster")
    p_receive.add_argument('-c', "--count", metavar="COUNT", type=int, default=1, help="number of codes to receive, use 0 for infinite")
    p_receive.add_argument('device', metavar='TYPE:ARGS', type=str, help='Target device type/info')
    p_receive.set_defaults(func=do_receive)

    args = parser.parse_args()
    if args.func is None:
        parser.help()
    args.func(args)
