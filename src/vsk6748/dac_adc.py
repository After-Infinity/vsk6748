"""DAC1 / ADC1 sketches. They need the kit's common files in the CCS project."""
from .sketch import Sketch, _csv
from .design import _wave_table


def dac_wave(kind="sine", freq=1000.0, samples=64, amplitude=2047, offset=2048,
             cpu_hz=30_000_000, pll=None):
    """Waveform on DAC1: sine, sawtooth, square or triangle (the manual's DAC experiments).
    The table is made in Python; the DSP plays it at freq*samples updates per second,
    timed with the CPU cycle counter. freq is only accurate if cpu_hz is calibrated and
    the SPI transfer is faster than one sample period (the DSP then simply runs slower)."""
    if freq <= 0:
        raise ValueError("freq must be positive")
    tab = _wave_table(kind, samples, amplitude, offset)
    ticks = int(round(cpu_hz / (freq * samples)))
    s = Sketch(cpu_hz, "dac_%s_%gHz" % (kind, freq), kit=True, pll=pll)
    if ticks < 400:
        s.notes.append("%g Hz with %d samples needs %d CPU cycles per DAC write; the SPI write may be "
                       "slower than that, so the real frequency can be lower. Use fewer samples or a "
                       "lower frequency." % (freq, samples, ticks))
    s.add_globals("#define WAVE_N %d\n#define WAVE_TICKS %du\nstatic const uint16_t wave[WAVE_N] = {\n    %s\n};\n"
                  "static uint32_t pace_next;" % (samples, ticks, _csv(tab)))
    s.add_setup("kitInit();\npace_next = cyclesNow();")
    s.add_loop("int i;\nfor (i = 0; i < WAVE_N; i++) {\n    dacWrite(wave[i]);\n"
               "    pace_next += WAVE_TICKS;\n    cyclesWaitUntil(pace_next);\n}")
    return s


def adc_to_dac(cpu_hz=30_000_000, pll=None):
    """ADCLOOP: whatever is on ADC1 (CH1) appears on DAC1."""
    s = Sketch(cpu_hz, "adc_to_dac", kit=True, pll=pll)
    s.add_setup("kitInit();")
    s.add_loop("dacWrite(adcRead());")
    return s
