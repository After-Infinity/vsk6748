"""Registry of the ready-made sketch generators (used by list_presets() and the command line)."""
from .leds import blink, chase, knight_rider, switch_to_led, binary_counter, calibration
from .dac_adc import dac_wave, adc_to_dac
from .filters import fir, iir
from .demos import convolution, correlation
from .audio import audio_loopback, audio_tone, mic_meter, audio_fsk

PRESETS = {f.__name__: f for f in (
    blink, chase, knight_rider, switch_to_led, binary_counter, calibration,
    dac_wave, adc_to_dac,
    fir, iir,
    convolution, correlation,
    audio_loopback, audio_tone, mic_meter, audio_fsk,
)}


def list_presets():
    """Return {name: one-line description} for every ready-made sketch generator."""
    return {name: fn.__doc__.strip().splitlines()[0] for name, fn in PRESETS.items()}
