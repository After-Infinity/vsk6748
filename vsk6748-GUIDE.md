# vsk6748 - user guide

`vsk6748` is a Python library that writes a complete **`main.c`** for the VSK-6748 (TMS320C6748) DSP kit.
You describe what you want in Python (or in Arduino-style C), run the script, then **copy `main.c` into
your Code Composer Studio (CCS) project**, Build, Debug, Resume.

---------------------------------------------------------------------------------------------------

## 1. What you need

| Item | Needed for |
|---|---|
| Python 3.8 or newer | the library itself (it has no other Python dependencies) |
| Code Composer Studio + the kit connected | building and running `main.c` (see section 8) |
| **The VSK-6748 common files** from your lab/CD (`VSK_6748.h`, `evmc6748.c` ...) | **DAC, ADC and audio only.** LEDs, switches, timing and the algorithm demos do not need them |
| `numpy`, `sounddevice` (optional) | only the audio-FSK receiver on the PC |

## 2. Install

Unzip the project, then in that folder:

```
pip install .
```

Or skip installing: keep your script next to the `src` folder and add `sys.path.insert(0, "src")`
(`make_main.py` already does this).

Check it works:

```
python -m vsk6748 list
python -m vsk6748 info
```

## 3. The 60-second start

```python
import vsk6748 as vsk
vsk.blink(led=1, on_ms=1000, off_ms=1000).write("main.c")
```

Run it, open `main.c`, select all, copy, paste over the `main.c` in your CCS project, then
**Build -> Debug -> Resume (F8)**. LED1 should blink.

No Python code needed? Use the command line:

```
python -m vsk6748 gen blink --param led=1 --param on_ms=1000 --param off_ms=1000 -o main.c
```

or edit and run the ready-made `make_main.py`.

## 4. Calibrate the timing once (important)

All delays and sample rates are counted in CPU clock ticks. The library does not know your real CPU
clock, so the default (30 MHz) may be wrong. Fix it once:

1. `python -m vsk6748 gen calibration -o main.c` -> run it on the board (LED1 should be on for "10 seconds").
2. Time one "on" period with a stopwatch, e.g. 12.5 s.
3. `python -m vsk6748 calibrate 30000000 10 12.5` -> prints the real value (24000000).
4. Pass it everywhere: `vsk.blink(cpu_hz=24_000_000)`, or `cpu_hz=` on any preset or `Sketch`.

## 5. Ready-made presets

Every function returns a `Sketch`; call `.write("main.c")` to create the file.

### LEDs and DIP switches (no kit files needed)
| Function | What it does |
|---|---|
| `blink(led=1, on_ms=1000, off_ms=1000)` | one LED (1..8) on/off |
| `chase(on_ms, off_ms)` | each LED on then off, LED1 to LED8 |
| `knight_rider(step_ms)` | one LED sweeps back and forth |
| `switch_to_led()` | LED n copies DIP switch n |
| `binary_counter(step_ms)` | LEDs count in binary |
| `calibration(seconds=10)` | for timing calibration |

### DAC and ADC (need the kit files)
| Function | What it does |
|---|---|
| `dac_wave(kind, freq, samples=64, amplitude=2047, offset=2048)` | `kind` = sine, sawtooth, square, triangle on **DAC1** |
| `adc_to_dac()` | ADCLOOP: **ADC1 (CH1)** input appears on DAC1 |

Values are 12-bit (0..4095, about 0..3.3 V). The DAC update rate is limited by the SPI transfer
speed. If `freq x samples` is too high the library prints a note, and the real frequency will be lower.

### Filters (need the kit files)
```python
vsk.fir("lowpass", fs=8000, cutoff=1000, taps=45)            # kind: lowpass, highpass, bandpass, bandstop
vsk.fir("bandpass", fs=8000, cutoff=(1000, 2000), taps=65)
vsk.iir("lowpass", fs=8000, cutoff=1000, order=4)            # order 2 or 4 for LP/HP; 2 for BP/BS
vsk.iir("bandstop", fs=8000, cutoff=(800, 1600))
```
The filter is designed in Python, then runs on the board: **ADC1 -> filter -> DAC1** at a fixed
sample rate `fs` (timed with the CPU cycle counter, so `cpu_hz` must be calibrated). The input is
assumed to be centred on mid-scale (2048, i.e. about 1.65 V DC offset); the output is clamped to 0..4095.

Check a design on the PC first:
```python
h = vsk.fir_quantize(vsk.fir_design("lowpass", 8000, 1000, 45))
vsk.freq_response(h, [32768.0], 8000, 3000)                   # gain at 3 kHz
```
`vsk.fir_reference(h, samples)` and `vsk.iir_reference(sections, samples)` compute exactly what the
board computes, so you can compare the DAC output with Python.

### Algorithm demos (plain C, results appear in the CCS console, also run in the simulator)
```python
vsk.convolution([1, 2, 3, 4], [1, -1, 2])                       # linear
vsk.convolution([1, 2, 3, 4], [1, 1, 1], circular=True, n=4)
vsk.correlation([1, 2, 3, 4], [2, 0, 1])                       # cross-correlation
vsk.correlation([1, 2, 3, 4])                                   # auto-correlation
```
The expected answers are available in Python: `vsk.linear_convolution`, `vsk.circular_convolution`,
`vsk.cross_correlation`, `vsk.auto_correlation`.

### Audio codec (need the kit files; microphone on MIC IN, output on SKR OUT)
| Function | What it does |
|---|---|
| `audio_loopback(gain=3)` | mic to output (the lab manual's experiment) |
| `audio_tone(freq, amplitude, fs=48000)` | steady sine from the output jack |
| `mic_meter(divisor=400)` | mic level on the 8 LEDs; buffer `mic_buf` to graph in CCS |
| `audio_fsk(text, baud=200)` | sends text as audio tones to the PC line-in |

**Seeing the mic without a speaker:** use `mic_meter()`. In CCS, open *Tools -> Graph -> Single Time*,
start address `mic_buf`, 16-bit signed, length 512.

**Board -> PC data link:** run `audio_fsk("HELLO")`, connect SKR OUT to the PC line-in, then on the PC
`pip install numpy sounddevice` and `python -m vsk6748 fsk-rx --seconds 10`. It auto-detects the codec
sample rate and prints `RECEIVED: HELLO`.

## 6. Write your own Arduino-style sketch

```python
s = vsk.Sketch(cpu_hz=30_000_000)
s.add_globals("int count = 0;")
s.add_setup("pinMode(LED1, OUTPUT);")
s.add_loop("digitalWrite(LED1, count++ & 1); delay(500);")
s.write("main.c")
```
or write a text file with `setup()` and `loop()` (any extension, e.g. `my.ino`) and run
`vsk.Sketch.from_file("my.ino").write("main.c")` / `python -m vsk6748 build my.ino -o main.c`.

Functions you can use inside a sketch:

| Group | Functions |
|---|---|
| always | `delay(ms)`, `delayMicroseconds(us)`, `millis()`, `cyclesNow()`, `cyclesWaitUntil(t)`, `printf(...)` |
| pins | `LED1..LED8`, `SW1..SW8`, `pinMode(pin, INPUT/OUTPUT)`, `digitalWrite(pin, HIGH/LOW)`, `digitalRead(pin)` |
| LED/switch helpers | `ledsInit()`, `switchesInit()`, `ledWrite(n, v)`, `ledsWrite(mask8)`, `switchesRead()` |
| DAC/ADC | `kitInit()` first, then `dacWrite(0..4095)`, `adcRead()` |
| audio | `audioInit()` first, then `audioRead()`, `audioWrite(v)`, `audioWriteStereo(v)` |

Call `pinMode`/`ledsInit`/`switchesInit`/`kitInit`/`audioInit` in `setup()`. The library warns if you forget.
`loop()` runs forever, like Arduino.

`Sketch(...)` options: `cpu_hz`, `kit=True/False` (normally automatic), `pll=(0,48,1,0,1,11,5)` (calls the
kit's `config_pll0`, as in the manual's filter experiments - changes the CPU speed, so recalibrate),
`audio_rx="XBUF4"` (default, as in the lab manual) or `"RBUF4"` (the name in the TI manual; try it if the
microphone reads zero).

## 7. Does it support the kit's ADC and DAC connectors?

**Yes, for ADC channel 1 and DAC channel 1** - the channels the lab manual uses in every experiment
(`adcRead()` = ADC1 CH1, `dacWrite()` = DAC1). Behind the scenes it uses the same calls as your lab
code, so **the kit's common files must be in your CCS project** (the manual's Step 8): they contain the
SPI setup (`Spi_inti`) that this library calls but cannot replace.

**Not supported:** DAC2 and ADC channels 2 and up. The manual only shows the command word for channel 1
("refer manual" for the others) and gives no part numbers, so guessing would be unsafe. If you have the
board schematic or the common files, send them and support can be added.

Run `python -m vsk6748 info` to see the verification status of every feature.

## 8. Running main.c in CCS

1. Connect and power the kit; make sure *Test Connection* succeeds for your XDS100v2 target configuration.
2. New CCS project (C674x Floating-point DSP / TMS320C6748), "Empty Project (with main.c)".
3. **DAC/ADC/audio presets only:** add the kit's common files: *Project -> Properties -> Build -> C6000
   Compiler -> Include Options* (add the folder with `VSK_6748.h`) and put the kit's `.c` files (e.g.
   `evmc6748.c`) in the project. Do **not** also paste the manual's whole experiment listing; it has its own `main()`.
4. Paste the generated code over `main.c`. Build. Debug. Resume (F8).
5. LED programs: watch the board. printf programs: open the CCS Console. Mic meter: LEDs and the `mic_buf` graph.

## 9. What is verified and what is not

* Register offsets, GPIO8[8..15] / GPIO0[0..7] pin-mux fields, PSC1 GPIO module and kick keys match the TI TRM (SPRUH79C).
* The generated C compiles and behaves correctly **on a PC against fake hardware** (43 automated tests):
  pin masks, timing, DAC tables, FIR/IIR output vs Python models, audio paths, FSK decoding.
* **Not tested on the real board or with the TI compiler.** Still unverified: LED bit order vs. the physical
  D52..D59 order, DIP-switch polarity, the codec sample rate (48 kHz assumed), the 16-bit audio sample
  format, and your actual CPU clock.

## 10. Troubleshooting

| Problem | Try |
|---|---|
| Build error "redefinition of delay/millis/..." | a name clashes with the kit's headers; tell the maintainer the name |
| Build error "cannot open VSK_6748.h" | add the kit's common folder to *Include Options* |
| Linker "undefined reference Spi_inti / MCASP_init" | the kit's `.c` files are not in the project |
| Delays are too long/short | calibrate (section 4) |
| LEDs do not change | open Memory Browser at `0x01E260B4` and see if the value changes |
| Mic samples all 0 | `Sketch(..., audio_rx="RBUF4")` |
| DAC frequency too low | lower `freq` or `samples`; the SPI write is the limit |
| Filter output looks clipped/offset | input must be centred around 1.65 V (code 2048) |

## 11. Tests

```
python -m unittest discover -s tests -v          # needs gcc for the C-on-PC tests
```
