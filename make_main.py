"""make_main.py - edit the CHOICE section, run `python make_main.py`, copy the new main.c into CCS.

Works with the library installed (pip install .) or with the folder src/ next to this file."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
import vsk6748 as vsk

CPU_HZ = 30_000_000          # your calibrated CPU clock: python -m vsk6748 calibrate 30000000 10 <seconds>

# ---------------- CHOICE: keep exactly one line active ----------------
sketch = vsk.blink(led=1, on_ms=1000, off_ms=1000, cpu_hz=CPU_HZ)
# sketch = vsk.chase(on_ms=300, off_ms=300, cpu_hz=CPU_HZ)
# sketch = vsk.switch_to_led(cpu_hz=CPU_HZ)
# sketch = vsk.dac_wave("sine", freq=1000, cpu_hz=CPU_HZ)
# sketch = vsk.adc_to_dac(cpu_hz=CPU_HZ)
# sketch = vsk.fir("lowpass", fs=8000, cutoff=1000, cpu_hz=CPU_HZ)
# sketch = vsk.iir("lowpass", fs=8000, cutoff=1000, order=4, cpu_hz=CPU_HZ)
# sketch = vsk.convolution([1, 2, 3, 4], [1, -1, 2], cpu_hz=CPU_HZ)
# sketch = vsk.audio_loopback(gain=3, cpu_hz=CPU_HZ)
# sketch = vsk.mic_meter(cpu_hz=CPU_HZ)
# -----------------------------------------------------------------------

# Your own Arduino-style logic instead of a preset:
# sketch = vsk.Sketch(cpu_hz=CPU_HZ)
# sketch.add_setup("ledsInit();")
# sketch.add_loop("ledsWrite(0xAA); delay(500); ledsWrite(0x55); delay(500);")

path = sketch.write("main.c")
print("Wrote", os.path.abspath(path), "- copy its contents into main.c of your CCS project.")
