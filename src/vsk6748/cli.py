"""Command line interface: python -m vsk6748 ...  (or the `vsk6748` command after pip install)."""
import argparse
import ast
import sys

from . import __version__
from .sketch import Sketch
from .leds import cpu_hz_from_stopwatch
from .presets import PRESETS, list_presets


def _parse_value(v):
    try:
        return ast.literal_eval(v)
    except (ValueError, SyntaxError):
        return v


def main(argv=None):
    p = argparse.ArgumentParser(prog="vsk6748", description="Arduino-style main.c generator for the VSK-6748 kit")
    p.add_argument("--version", action="version", version="vsk6748 " + __version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", aliases=["preset"], help="generate main.c from a ready-made preset (see 'list')")
    g.add_argument("name")
    g.add_argument("-o", "--out", default="main.c", help="output file (default main.c)")
    g.add_argument("--param", action="append", default=[], metavar="KEY=VALUE",
                   help="argument for the preset; repeat it. Example: --param freq=1000 --param kind=sine")

    b = sub.add_parser("build", help="wrap an Arduino-style sketch file (setup()/loop()) into main.c")
    b.add_argument("sketch")
    b.add_argument("-o", "--out", default="main.c")
    b.add_argument("--cpu-hz", type=int, default=30_000_000)
    b.add_argument("--kit", action="store_true", help="force the DAC/ADC/audio layer on")

    sub.add_parser("list", help="list all presets")
    sub.add_parser("info", help="show what is supported and how well it is verified")

    c = sub.add_parser("calibrate", help="compute the real CPU clock from a stopwatch measurement")
    c.add_argument("current_hz", type=float)
    c.add_argument("seconds_wanted", type=float)
    c.add_argument("seconds_measured", type=float)

    f = sub.add_parser("fsk-rx", help="PC receiver for audio_fsk (needs: pip install numpy sounddevice)")
    f.add_argument("--wav")
    f.add_argument("--seconds", type=float, default=10)
    f.add_argument("--measure", action="store_true")

    a = p.parse_args(argv)
    if a.cmd == "list":
        for k, v in list_presets().items():
            print("%-16s %s" % (k, v))
    elif a.cmd == "info":
        from .hardware import support_table
        print(support_table())
    elif a.cmd == "build":
        s = Sketch.from_file(a.sketch, a.cpu_hz, kit=True if a.kit else None)
        print("wrote", s.write(a.out))
    elif a.cmd in ("gen", "preset"):
        if a.name not in PRESETS:
            sys.exit("unknown preset %r; run: vsk6748 list" % a.name)
        kw = {}
        for item in a.param:
            if "=" not in item:
                sys.exit("--param needs KEY=VALUE, got %r" % item)
            k, v = item.split("=", 1)
            kw[k] = _parse_value(v)
        try:
            sketch = PRESETS[a.name](**kw)
        except TypeError as e:
            sys.exit("bad --param for %s: %s" % (a.name, e))
        print("wrote", sketch.write(a.out))
    elif a.cmd == "calibrate":
        hz = cpu_hz_from_stopwatch(a.current_hz, a.seconds_wanted, a.seconds_measured)
        print("Use cpu_hz = %d  (or --param cpu_hz=%d)" % (hz, hz))
    elif a.cmd == "fsk-rx":
        from . import fsk_rx
        fsk_rx.main(["--seconds", str(a.seconds)] + (["--wav", a.wav] if a.wav else [])
                    + (["--measure"] if a.measure else []))
    return 0
