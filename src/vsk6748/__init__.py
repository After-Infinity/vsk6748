"""vsk6748 - Arduino-style code generator for the VSK-6748 (TMS320C6748) DSP kit.

Generate a complete ``main.c`` from Python, then paste it into a Code Composer Studio project.

    import vsk6748 as vsk

    vsk.blink(led=3, on_ms=250, off_ms=750).write("main.c")
    vsk.dac_wave("sine", freq=1000).write("main.c")
    vsk.fir("lowpass", fs=8000, cutoff=1000).write("main.c")

    s = vsk.Sketch(cpu_hz=30_000_000)                  # or write your own Arduino-style sketch
    s.add_setup("pinMode(LED1, OUTPUT);")
    s.add_loop("digitalWrite(LED1, HIGH); delay(500); digitalWrite(LED1, LOW); delay(500);")
    s.write("main.c")

See docs/GUIDE.md for the full guide, ``vsk6748 list`` for all presets and
``vsk6748 info`` for what is verified on the hardware.
"""
from .sketch import Sketch, KIT_NOTE
from .leds import (blink, chase, knight_rider, switch_to_led, binary_counter, calibration,
                   cpu_hz_from_stopwatch)
from .dac_adc import dac_wave, adc_to_dac
from .filters import fir, iir
from .demos import convolution, correlation
from .audio import audio_loopback, audio_tone, mic_meter, audio_fsk
from .design import (freq_response, fir_design, fir_quantize, fir_reference, iir_design,
                     iir_reference, linear_convolution, circular_convolution,
                     cross_correlation, auto_correlation)
from .presets import PRESETS, list_presets
from .hardware import SUPPORT, support_table

__version__ = "1.0.0"

__all__ = [
    "Sketch", "KIT_NOTE", "PRESETS", "list_presets", "SUPPORT", "support_table", "cpu_hz_from_stopwatch",
    "blink", "chase", "knight_rider", "switch_to_led", "binary_counter", "calibration",
    "dac_wave", "adc_to_dac", "fir", "iir", "convolution", "correlation",
    "audio_loopback", "audio_tone", "mic_meter", "audio_fsk",
    "freq_response", "fir_design", "fir_quantize", "fir_reference", "iir_design", "iir_reference",
    "linear_convolution", "circular_convolution", "cross_correlation", "auto_correlation",
]
