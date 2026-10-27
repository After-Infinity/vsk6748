# vsk6748

Arduino-style `main.c` generator for the **VSK-6748 (TMS320C6748)** DSP kit.
Write Python, get a `main.c`, paste it into Code Composer Studio.

```python
import vsk6748 as vsk
vsk.blink(led=1, on_ms=1000, off_ms=1000).write("main.c")
vsk.fir("lowpass", fs=8000, cutoff=1000).write("main.c")
```

* LEDs, DIP switches, timing, DAC1/ADC1, FIR/IIR filters, convolution/correlation, audio codec
* Arduino-style API for your own sketches: `pinMode`, `digitalWrite`, `delay`, `dacWrite`, `adcRead`, `audioRead` ...
* Command line: `python -m vsk6748 list | info | gen <preset> | build <file> | calibrate`

Install: `pip install .` - Full guide: [docs/GUIDE.md](docs/GUIDE.md)

Status: tested on a PC against fake hardware; **not yet tested on the real board or the TI compiler**.
DAC/ADC/audio code needs the kit's common files (VSK_6748.h, evmc6748.c ...) in the CCS project.
# vsk6748
