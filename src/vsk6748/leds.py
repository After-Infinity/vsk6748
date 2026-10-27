"""LED / DIP-switch sketches. These need no kit library files."""
from .sketch import Sketch


def blink(led=1, on_ms=1000, off_ms=1000, cpu_hz=30_000_000):
    """One LED on for on_ms, off for off_ms."""
    if not 1 <= led <= 8:
        raise ValueError("led must be 1..8")
    s = Sketch(cpu_hz, "blink")
    s.add_setup("pinMode(LED%d, OUTPUT);" % led)
    s.add_loop("digitalWrite(LED%d, HIGH);\ndelay(%d);\ndigitalWrite(LED%d, LOW);\ndelay(%d);"
               % (led, on_ms, led, off_ms))
    return s


def chase(on_ms=300, off_ms=300, cpu_hz=30_000_000):
    """Each LED turns on, then off, one after another (LED1 -> LED8)."""
    s = Sketch(cpu_hz, "chase")
    s.add_setup("ledsInit();")
    s.add_loop("uint32_t i;\nfor (i = 1; i <= 8; i++) {\n    ledWrite(i, HIGH);\n    delay(%d);\n"
               "    ledWrite(i, LOW);\n    delay(%d);\n}" % (on_ms, off_ms))
    return s


def knight_rider(step_ms=80, cpu_hz=30_000_000):
    """A single LED sweeps back and forth."""
    s = Sketch(cpu_hz, "knight_rider")
    s.add_setup("ledsInit();")
    s.add_loop("int i;\nfor (i = 0; i < 8; i++) { ledsWrite(1u << i); delay(%d); }\n"
               "for (i = 6; i > 0; i--) { ledsWrite(1u << i); delay(%d); }" % (step_ms, step_ms))
    return s


def switch_to_led(cpu_hz=30_000_000):
    """LED n copies DIP switch n (the board's switch polarity is unverified)."""
    s = Sketch(cpu_hz, "switch_to_led")
    s.add_setup("ledsInit();\nswitchesInit();")
    s.add_loop("ledsWrite(switchesRead());")
    return s


def binary_counter(step_ms=500, cpu_hz=30_000_000):
    """LEDs count 0..255 in binary."""
    s = Sketch(cpu_hz, "binary_counter")
    s.add_globals("static uint32_t count = 0;")
    s.add_setup("ledsInit();")
    s.add_loop("ledsWrite(count++);\ndelay(%d);" % step_ms)
    return s


def calibration(cpu_hz=30_000_000, seconds=10):
    """LED1 on for `seconds` (by the assumed clock), then off for the same time.
    Time one 'on' period with a stopwatch, then run:
        python vsk6748.py calibrate <cpu_hz> <seconds> <measured>"""
    s = Sketch(cpu_hz, "calibration")
    s.add_setup("pinMode(LED1, OUTPUT);")
    s.add_loop("digitalWrite(LED1, HIGH);\ndelay(%d);\ndigitalWrite(LED1, LOW);\ndelay(%d);"
               % (seconds * 1000, seconds * 1000))
    return s


def cpu_hz_from_stopwatch(current_hz, seconds_wanted, seconds_measured):
    """If a '10 s' delay really took 12.5 s, the true clock is current*10/12.5."""
    if seconds_measured <= 0 or seconds_wanted <= 0:
        raise ValueError("seconds must be positive")
    return int(round(current_hz * seconds_wanted / seconds_measured))
