"""Plain-C algorithm demos (results printed to the CCS console; they also run in the simulator)."""
from .sketch import Sketch, _csv


def _demo(title, cpu_hz):
    s = Sketch(cpu_hz, title, kit=False, gpio=False)
    s.notes.append("Plain C + printf: results appear in the CCS Console. Runs in the CCS simulator too.")
    return s


def convolution(x, h, circular=False, n=None, cpu_hz=30_000_000):
    """Linear (default) or circular convolution of two integer lists, printed on the console."""
    x, h = [int(v) for v in x], [int(v) for v in h]
    if circular:
        n = n or max(len(x), len(h))
        n_out = n
    else:
        n_out = len(x) + len(h) - 1
    s = _demo("%s_convolution" % ("circular" if circular else "linear"), cpu_hz)
    s.add_globals("#define NX %d\n#define NH %d\n#define NY %d\nstatic const int x[NX] = {%s};\n"
                  "static const int h[NH] = {%s};\nstatic int y[NY];"
                  % (len(x), len(h), n_out, _csv(x), _csv(h)))
    if circular:
        body = ("int i, k, xv, hv;\nfor (i = 0; i < NY; i++) {\n    y[i] = 0;\n"
                "    for (k = 0; k < NY; k++) {\n"
                "        xv = (k < NX) ? x[k] : 0;\n"
                "        hv = (((i - k) % NY + NY) % NY < NH) ? h[((i - k) %% NY + NY) %% NY] : 0;\n"
                "        y[i] += xv * hv;\n    }\n}\n").replace("%%", "%")
        title = "circular convolution (N = %d)" % n_out
    else:
        body = ("int i, k;\nfor (i = 0; i < NY; i++) {\n    y[i] = 0;\n"
                "    for (k = 0; k < NX; k++) {\n"
                "        if (i - k >= 0 && i - k < NH) y[i] += x[k] * h[i - k];\n    }\n}\n")
        title = "linear convolution"
    s.add_setup(body + 'printf("%s\\n");\nfor (i = 0; i < NY; i++) printf("y[%%d] = %%d\\n", i, y[i]);' % title)
    s.add_loop("delay(1000);")
    return s


def correlation(x, y=None, cpu_hz=30_000_000):
    """Cross-correlation of x and y (auto-correlation of x if y is None), printed as lag: value."""
    x = [int(v) for v in x]
    yy = [int(v) for v in (y if y is not None else x)]
    s = _demo("%s_correlation" % ("auto" if y is None else "cross"), cpu_hz)
    s.add_globals("#define NX %d\n#define NY %d\nstatic const int x[NX] = {%s};\n"
                  "static const int y[NY] = {%s};"
                  % (len(x), len(yy), _csv(x), _csv(yy)))
    s.add_setup("int lag, n, acc;\n"
                'printf("%s\\n");\n'
                "for (lag = -(NY - 1); lag < NX; lag++) {\n    acc = 0;\n"
                "    for (n = 0; n < NX; n++) {\n"
                "        if (n - lag >= 0 && n - lag < NY) acc += x[n] * y[n - lag];\n    }\n"
                '    printf("r[%%d] = %%d\\n", lag, acc);\n}' % ("auto-correlation" if y is None else "cross-correlation"))
    s.add_loop("delay(1000);")
    return s
