"""Compile a generated main.c against fake registers/hardware (harness.c) and run it."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HAVE_GCC = shutil.which("gcc") is not None
needs_gcc = unittest.skipUnless(HAVE_GCC, "gcc not found (needed to compile the generated C on the PC)")


def run(sketch, loops=1, in01="0", adc=None, rx=None, step=100):
    """Build and run `sketch` for `loops` calls of loop(); return a dict of what the 'hardware' saw."""
    tmp = tempfile.mkdtemp()
    try:
        main_c = os.path.join(tmp, "main.c")
        sketch.write(main_c, quiet=True)
        exe = os.path.join(tmp, "t_exe")
        r = subprocess.run(
            ["gcc", "-std=c99", "-Wall", "-Wextra", "-Wno-unused-function", "-Wdeclaration-after-statement",
             "-O1", '-DGENERATED="%s"' % main_c, "-DCLK_HZ=%du" % sketch.cpu_hz, "-DSTEP=%du" % step,
             "-o", exe, os.path.join(HERE, "harness.c"), "-lm"],
            capture_output=True, text=True)
        if r.returncode != 0 or r.stderr.strip():
            raise AssertionError("compiler problem:\n" + r.stderr)
        args = [exe, str(loops), in01]
        for data in (adc, rx):
            if data is None:
                args.append("-")
            else:
                path = os.path.join(tmp, "in%d.txt" % len(args))
                with open(path, "w") as f:
                    f.write("\n".join(str(int(x)) for x in data))
                args.append(path)
        out = subprocess.run(args, capture_output=True, text=True).stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return dict(
        out=out,
        T=[(float(a), int(b, 16)) for a, b in re.findall(r"^T (\S+) (\S+)$", out, re.M)],
        R=dict(re.findall(r"^R (\S+) (\S+)$", out, re.M)),
        D=[int(x) for x in re.findall(r"^D (\d+)$", out, re.M)],
        A=[int(x) for x in re.findall(r"^A (-?\d+)$", out, re.M)],
        clk=int(re.search(r"^C (\d+)$", out, re.M).group(1)),
    )
