"""Pure-Python signal-processing helpers: filter design, reference models, convolution and
correlation. No hardware, no C, no third-party packages.

The `*_reference` functions model exactly what the generated C code computes, so you can check
the board's output against Python."""
import math

def freq_response(b, a, fs, f):
    """Magnitude (linear) of H(z)=B/A at frequency f (Hz). a may be [1]."""
    w = 2 * math.pi * f / fs
    num = sum(bk * complex(math.cos(-w * k), math.sin(-w * k)) for k, bk in enumerate(b))
    den = sum(ak * complex(math.cos(-w * k), math.sin(-w * k)) for k, ak in enumerate(a))
    return abs(num / den)


def _check_band(kind, cutoff, fs):
    if kind in ("lowpass", "highpass"):
        edges = [cutoff]
    elif kind in ("bandpass", "bandstop"):
        if not (isinstance(cutoff, (tuple, list)) and len(cutoff) == 2 and cutoff[0] < cutoff[1]):
            raise ValueError("%s needs cutoff=(low_hz, high_hz)" % kind)
        edges = list(cutoff)
    else:
        raise ValueError("kind must be lowpass, highpass, bandpass or bandstop")
    for e in edges:
        if not 0 < e < fs / 2:
            raise ValueError("cutoff %g Hz must be between 0 and fs/2 = %g Hz" % (e, fs / 2))
    return edges


def fir_design(kind, fs, cutoff, taps=45):
    """Hamming-window FIR design (floating point). taps is forced to be odd.
    cutoff: Hz, or (low, high) for bandpass/bandstop."""
    edges = _check_band(kind, cutoff, fs)
    n = taps if taps % 2 == 1 else taps + 1
    m = (n - 1) / 2

    def lp(fc):
        wc = 2 * math.pi * fc / fs
        return [wc / math.pi if k == m else math.sin(wc * (k - m)) / (math.pi * (k - m)) for k in range(n)]

    if kind == "lowpass":
        ideal = lp(edges[0])
    elif kind == "highpass":
        ideal = [(1.0 if k == m else 0.0) - v for k, v in enumerate(lp(edges[0]))]
    elif kind == "bandpass":
        ideal = [u - v for u, v in zip(lp(edges[1]), lp(edges[0]))]
    else:
        ideal = [(1.0 if k == m else 0.0) - (u - v) for k, (u, v) in enumerate(zip(lp(edges[1]), lp(edges[0])))]
    win = [0.54 - 0.46 * math.cos(2 * math.pi * k / (n - 1)) for k in range(n)]
    h = [x * w for x, w in zip(ideal, win)]
    ref_f = {"lowpass": 0.0, "highpass": fs / 2, "bandpass": sum(edges) / 2, "bandstop": 0.0}[kind]
    g = freq_response(h, [1.0], fs, ref_f)
    return [x / g for x in h]


def fir_quantize(h, bits=15):
    """Round FIR taps to signed integers (Q15 by default, like the manual's coefficient tables)."""
    lim = (1 << bits) - 1
    return [int(max(-lim, min(lim, round(x * (1 << bits))))) for x in h]


def fir_reference(hq, adc_samples):
    """Python model of exactly what the DSP computes (integer FIR, 12-bit in/out, DC removed)."""
    n = len(hq)
    xb = [0] * n
    out = []
    for adc in adc_samples:
        xb = [adc - 2048] + xb[:-1]
        acc = sum(hq[k] * xb[k] for k in range(n))
        y = (acc >> 15) + 2048
        out.append(max(0, min(4095, y)))
    return out


def iir_design(kind, fs, cutoff, order=2, q=None):
    """Biquad IIR design (RBJ cookbook). Returns a list of sections (b0,b1,b2,a1,a2), a0 = 1.
    lowpass/highpass: order 2 (Q default 0.7071) or 4 (cascade of two Butterworth sections).
    bandpass/bandstop: cutoff=(low, high), order 2."""
    edges = _check_band(kind, cutoff, fs)
    if kind in ("lowpass", "highpass"):
        if order == 2:
            qs = [q if q else 1 / math.sqrt(2)]
        elif order == 4:
            qs = [0.5411961, 1.3065630]
        else:
            raise ValueError("order must be 2 or 4")
        f0s = [edges[0]] * len(qs)
    else:
        if order != 2:
            raise ValueError("bandpass/bandstop support order 2 only")
        f0 = math.sqrt(edges[0] * edges[1])
        qs = [f0 / (edges[1] - edges[0])]
        f0s = [f0]
    secs = []
    for f0, qq in zip(f0s, qs):
        w0 = 2 * math.pi * f0 / fs
        cw, sw = math.cos(w0), math.sin(w0)
        al = sw / (2 * qq)
        if kind == "lowpass":
            b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        elif kind == "highpass":
            b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        elif kind == "bandpass":
            b = [al, 0.0, -al]
        else:
            b = [1.0, -2 * cw, 1.0]
        a0 = 1 + al
        secs.append(tuple(v / a0 for v in (b[0], b[1], b[2], -2 * cw, 1 - al)))
    return secs


def iir_reference(sections, adc_samples):
    """Python model of the DSP's biquad cascade (double precision; the DSP uses float)."""
    st = [[0.0, 0.0, 0.0, 0.0] for _ in sections]   # x1, x2, y1, y2
    out = []
    for adc in adc_samples:
        v = float(adc - 2048)
        for (b0, b1, b2, a1, a2), z in zip(sections, st):
            y = b0 * v + b1 * z[0] + b2 * z[1] - a1 * z[2] - a2 * z[3]
            z[1], z[0], z[3], z[2] = z[0], v, z[2], y
            v = y
        f = max(0.0, min(4095.0, v + 2048.0))
        out.append(int(f + 0.5))
    return out


def linear_convolution(x, h):
    return [sum(x[k] * h[n - k] for k in range(len(x)) if 0 <= n - k < len(h))
            for n in range(len(x) + len(h) - 1)]


def circular_convolution(x, h, n=None):
    n = n or max(len(x), len(h))
    xp = list(x) + [0] * (n - len(x))
    hp = list(h) + [0] * (n - len(h))
    return [sum(xp[k] * hp[(i - k) % n] for k in range(n)) for i in range(n)]


def cross_correlation(x, y):
    """r_xy[l] = sum_n x[n]*y[n-l], for lags l = -(len(y)-1) .. len(x)-1.
    Returns a list of (lag, value)."""
    out = []
    for lag in range(-(len(y) - 1), len(x)):
        out.append((lag, sum(x[n] * y[n - lag] for n in range(len(x)) if 0 <= n - lag < len(y))))
    return out


def auto_correlation(x):
    return cross_correlation(x, x)


def _wave_table(kind, samples, amplitude, offset):
    if samples < 4:
        raise ValueError("samples must be >= 4")
    tab = []
    for i in range(samples):
        ph = i / samples
        if kind == "sine":
            v = math.sin(2 * math.pi * ph)
        elif kind == "sawtooth":
            v = 2 * ph - 1
        elif kind == "triangle":
            v = 4 * ph - 1 if ph < 0.5 else 3 - 4 * ph
        elif kind == "square":
            v = 1.0 if ph < 0.5 else -1.0
        else:
            raise ValueError("kind must be sine, sawtooth, square or triangle")
        tab.append(int(max(0, min(4095, round(offset + amplitude * v)))))
    return tab
