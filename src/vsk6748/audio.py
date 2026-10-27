"""Audio-codec sketches (MIC IN / SKR OUT). They need the kit's common files in the CCS project."""
import math

from .sketch import Sketch, _csv


def audio_loopback(gain=3, cpu_hz=30_000_000):
    """MIC IN -> SKR OUT, scaled by gain (the manual's Mic and Speaker experiment)."""
    s = Sketch(cpu_hz, "audio_loopback", kit=True)
    s.add_setup("audioInit();")
    s.add_loop("int32_t dat = audioRead();\naudioWrite(dat * %d);" % int(gain))
    return s


def audio_tone(freq=1000.0, amplitude=12000, fs=48000.0, cpu_hz=30_000_000):
    """A steady sine tone out of SKR OUT. fs is the codec sample rate (UNVERIFIED: 48000 assumed;
    the pitch scales with the real rate, so measure it and adjust)."""
    if not 0 < freq < fs / 2:
        raise ValueError("freq must be between 0 and fs/2")
    s = Sketch(cpu_hz, "audio_tone", kit=True)
    s.notes.append("Codec sample rate assumed %g Hz (unverified); if the pitch is off, scale fs." % fs)
    tab = [int(round(amplitude * math.sin(2 * math.pi * i / 256))) for i in range(256)]
    inc = int(round(freq * 4294967296.0 / fs)) & 0xFFFFFFFF
    s.add_globals("static const int16_t sine_tab[256] = {\n    %s\n};\n"
                  "static uint32_t phase = 0;\n#define PHASE_INC %du" % (_csv(tab, 16), inc))
    s.add_setup("audioInit();")
    s.add_loop("phase += PHASE_INC;\naudioWriteStereo(sine_tab[phase >> 24]);")
    return s


def mic_meter(divisor=400, loopback_gain=3, cpu_hz=30_000_000):
    """Mic level on the 8 LEDs, plus a 512-sample buffer `mic_buf` to graph in CCS
    (Tools -> Graph -> Single Time, 16-bit signed). Samples are assumed to be 16-bit values."""
    s = Sketch(cpu_hz, "mic_meter", kit=True, gpio=True)
    s.notes.append("Sample format (16-bit in the low half of the word) is inferred from the McASP "
                   "settings and unverified on hardware. Lower the divisor for a more sensitive meter.")
    s.add_globals("volatile int16_t mic_buf[512];\nvolatile uint32_t mic_idx = 0;\n"
                  "static uint32_t cnt = 0;\nstatic uint16_t peak = 0;")
    s.add_setup("ledsInit();\naudioInit();")
    s.add_loop("int32_t dat;\nint16_t smp;\nuint16_t a;\nuint32_t n;\n\n"
               "dat = audioRead();\naudioWrite(dat * %d);\n"
               "smp = (int16_t)dat;\nmic_buf[mic_idx] = smp;\nmic_idx = (mic_idx + 1) & 511;\n"
               "a = (smp < 0) ? (uint16_t)(-smp) : (uint16_t)smp;\nif (a > peak) peak = a;\n"
               "if (++cnt >= 4000) {\n    cnt = 0;\n    n = peak / %d;\n    if (n > 8) n = 8;\n"
               "    ledsWrite((1u << n) - 1u);\n    peak = 0;\n}" % (int(loopback_gain), int(divisor)))
    return s


def audio_fsk(text="HELLO DSP", baud=200, f_zero=1000.0, f_one=2000.0, fs=48000.0,
              amplitude=12000, cpu_hz=30_000_000):
    """Send `text` as audio FSK out of SKR OUT into a PC line-in; decode with fsk_rx.py.
    Frame: 0xAA 0xAA 0x7E, length, payload, checksum. Repeats about once a second."""
    data = text.encode("latin1")
    if not 1 <= len(data) <= 60:
        raise ValueError("text must be 1..60 bytes")
    s = Sketch(cpu_hz, "audio_fsk", kit=True)
    s.notes.append("Codec sample rate assumed %g Hz (unverified); fsk_rx.py auto-detects a different rate." % fs)
    inc0 = int(round(f_zero * 4294967296.0 / fs)) & 0xFFFFFFFF
    inc1 = int(round(f_one * 4294967296.0 / fs)) & 0xFFFFFFFF
    spb = int(fs / baud)
    tab = [int(round(amplitude * math.sin(2 * math.pi * i / 256))) for i in range(256)]
    msg = ", ".join(str(b) for b in data)
    s.add_globals(
        "#define FSK_SPB %d\n#define FSK_LEN %d\n#define INC_ZERO %du\n#define INC_ONE %du\n"
        "static const int16_t sine_tab[256] = {\n    %s\n};\n"
        "static const uint8_t msg[FSK_LEN] = {%s};\nstatic uint32_t phase = 0;\n\n"
        "static void send_bit(int b)\n{\n    uint32_t i, inc = b ? INC_ONE : INC_ZERO;\n"
        "    for (i = 0; i < FSK_SPB; i++) {\n        phase += inc;\n"
        "        audioWriteStereo(sine_tab[phase >> 24]);\n    }\n}\n\n"
        "static void send_byte(uint8_t v)\n{\n    int i;\n    for (i = 7; i >= 0; i--) send_bit((v >> i) & 1);\n}\n\n"
        "static void send_silence(uint32_t n)\n{\n    uint32_t i;\n    for (i = 0; i < n; i++) audioWriteStereo(0);\n}"
        % (spb, len(data), inc0, inc1, _csv(tab, 16), msg))
    s.add_setup("audioInit();")
    s.add_loop("uint8_t i, sum = 0;\n\nsend_silence(%du);\n"
               "send_byte(0xAA); send_byte(0xAA); send_byte(0x7E);\nsend_byte(FSK_LEN);\n"
               "for (i = 0; i < FSK_LEN; i++) { send_byte(msg[i]); sum = (uint8_t)(sum + msg[i]); }\n"
               "send_byte(sum);" % int(fs * 0.3))
    return s
