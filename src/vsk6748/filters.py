"""Real-time FIR / IIR filter sketches (ADC1 -> filter -> DAC1). Design happens in Python."""
from .sketch import Sketch, _csv
from .design import fir_design, fir_quantize, iir_design


def fir(kind="lowpass", fs=8000.0, cutoff=1000.0, taps=45, cpu_hz=30_000_000, pll=None):
    """Real-time FIR filter: ADC1 -> filter -> DAC1 at a fixed sample rate fs.
    Coefficients are designed in Python (Hamming window) and rounded to Q15.
    The input is treated as 0..4095 around mid-scale 2048 (a 1.65 V DC offset)."""
    h = fir_design(kind, fs, cutoff, taps)
    hq = fir_quantize(h)
    n = len(hq)
    ticks = int(round(cpu_hz / fs))
    s = Sketch(cpu_hz, "fir_%s" % kind, kit=True, pll=pll)
    if ticks < 60 * n:
        s.notes.append("fs=%g Hz leaves only %d CPU cycles per sample for %d taps plus the SPI "
                       "transfers; the real sample rate may be lower." % (fs, ticks, n))
    s.notes.append("Sample rate is set by timing (cpu_hz must be calibrated); input is assumed "
                   "centred on mid-scale (2048).")
    s.add_globals("#define FIR_N %d\n#define FIR_TICKS %du\nstatic const int16_t h[FIR_N] = {\n    %s\n};\n"
                  "static int16_t xb[FIR_N];\nstatic int pos = 0;\nstatic uint32_t pace_next;"
                  % (n, ticks, _csv(hq)))
    s.add_setup("int i;\nfor (i = 0; i < FIR_N; i++) xb[i] = 0;\nkitInit();\npace_next = cyclesNow();")
    s.add_loop("int k, idx;\nint32_t acc = 0, y;\n\n"
               "xb[pos] = (int16_t)((int)adcRead() - 2048);\nidx = pos;\n"
               "for (k = 0; k < FIR_N; k++) {\n    acc += (int32_t)h[k] * xb[idx];\n"
               "    if (--idx < 0) idx = FIR_N - 1;\n}\n"
               "if (++pos >= FIR_N) pos = 0;\n"
               "y = (acc >> 15) + 2048;\nif (y < 0) y = 0;\nif (y > 4095) y = 4095;\n"
               "dacWrite((uint32_t)y);\n"
               "pace_next += FIR_TICKS;\ncyclesWaitUntil(pace_next);")
    s.coefficients = hq
    return s


def iir(kind="lowpass", fs=8000.0, cutoff=1000.0, order=2, q=None, cpu_hz=30_000_000, pll=None):
    """Real-time IIR filter: ADC1 -> biquad(s) -> DAC1 at a fixed sample rate fs."""
    secs = iir_design(kind, fs, cutoff, order, q)
    ticks = int(round(cpu_hz / fs))
    s = Sketch(cpu_hz, "iir_%s" % kind, kit=True, pll=pll)
    s.notes.append("Sample rate is set by timing (cpu_hz must be calibrated); input is assumed "
                   "centred on mid-scale (2048).")
    rows = ",\n    ".join("{%s}" % ", ".join("%.9ff" % c for c in sec) for sec in secs)
    n = len(secs)
    s.add_globals("#define IIR_S %d\n#define IIR_TICKS %du\n"
                  "/* b0, b1, b2, a1, a2 (a0 = 1): y = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2 */\n"
                  "static const float bq[IIR_S][5] = {\n    %s\n};\n"
                  "static float zx1[IIR_S], zx2[IIR_S], zy1[IIR_S], zy2[IIR_S];\nstatic uint32_t pace_next;"
                  % (n, ticks, rows))
    s.add_setup("int i;\nfor (i = 0; i < IIR_S; i++) { zx1[i] = 0; zx2[i] = 0; zy1[i] = 0; zy2[i] = 0; }\n"
                "kitInit();\npace_next = cyclesNow();")
    s.add_loop("int k;\nfloat v, y, f;\n\n"
               "v = (float)((int)adcRead() - 2048);\n"
               "for (k = 0; k < IIR_S; k++) {\n"
               "    y = bq[k][0] * v + bq[k][1] * zx1[k] + bq[k][2] * zx2[k]\n"
               "        - bq[k][3] * zy1[k] - bq[k][4] * zy2[k];\n"
               "    zx2[k] = zx1[k];  zx1[k] = v;\n"
               "    zy2[k] = zy1[k];  zy1[k] = y;\n"
               "    v = y;\n}\n"
               "f = v + 2048.0f;\nif (f < 0.0f) f = 0.0f;\nif (f > 4095.0f) f = 4095.0f;\n"
               "dacWrite((uint32_t)(f + 0.5f));\n"
               "pace_next += IIR_TICKS;\ncyclesWaitUntil(pace_next);")
    s.sections = secs
    return s
