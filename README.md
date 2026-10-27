# vsk6748

**Arduino-style `main.c` generator for the VSK-6748 (TMS320C6748) DSP kit.**
Write a few lines of Python (or Arduino-style C), run it, and copy the generated `main.c` into
Code Composer Studio. No register hunting for the common jobs: LEDs, DIP switches, DAC, ADC,
FIR/IIR filters, convolution/correlation demos and the audio codec.

```python
import vsk6748 as vsk

vsk.blink(led=1, on_ms=1000, off_ms=1000).write("main.c")        # LED blink
vsk.dac_wave("sine", freq=1000).write("main.c")                  # sine on DAC1
vsk.fir("lowpass", fs=8000, cutoff=1000).write("main.c")         # ADC1 -> FIR -> DAC1
```

> **Status:** the generated C is compiled and run on a PC against fake hardware by 43 automated tests.
> It has **not yet been tested on a real board or with the TI compiler**. See
> [What is verified](#what-is-verified-and-what-is-not).

---

## Contents

1. [Requirements](#requirements)
2. [Install](#install)
3. [Quick start](#quick-start)
4. [Calibrate the timing once](#calibrate-the-timing-once)
5. [Ready-made presets](#ready-made-presets)
6. [Write your own Arduino-style sketch](#write-your-own-arduino-style-sketch)
7. [Command line](#command-line)
8. [ADC and DAC support](#adc-and-dac-support)
9. [Running main.c in Code Composer Studio](#running-mainc-in-code-composer-studio)
10. [What is verified and what is not](#what-is-verified-and-what-is-not)
11. [Troubleshooting](#troubleshooting)
12. [Project layout and tests](#project-layout-and-tests)

---

## Requirements

| Item | Needed for |
|---|---|
| Python 3.8 or newer | the library (no other Python packages needed) |
| Code Composer Studio (CCS) and the kit connected over its XDS100v2 USB port | building and running `main.c` |
| **The VSK-6748 common files** from your lab or the kit CD (`VSK_6748.h`, `evmc6748.c`, ...) | **DAC, ADC and audio only.** LEDs, switches, timing and the algorithm demos do not need them |
| `numpy` and `sounddevice` (optional) | only the board-to-PC audio link receiver |

## Install

```bash
git clone https://github.com/After-Infinity/vsk6748
cd vsk6748
pip install .
```

Or install straight from GitHub without cloning:

```bash
pip install git+https://github.com/After-Infinity/vsk6748
```

No install at all? Put your script in the repository folder and add `sys.path.insert(0, "src")` at the top
(`make_main.py` already does this).

Check that it works:

```bash
python -m vsk6748 list      # all presets
python -m vsk6748 info      # what is verified on the hardware
```

## Quick start

1. Write a script, for example `my_blink.py`:

   ```python
   import vsk6748 as vsk
   vsk.blink(led=1, on_ms=1000, off_ms=1000).write("main.c")
   ```

2. Run it: `python my_blink.py`. This creates `main.c`.
3. Open `main.c`, select all, copy, and paste it over the `main.c` in your CCS project.
4. In CCS: **Build, Debug, Resume (F8)**. LED1 blinks.

Prefer not to write Python? Two other ways to get the same file:

```bash
python -m vsk6748 gen blink --param led=1 --param on_ms=1000 --param off_ms=1000 -o main.c
```

or open `make_main.py`, keep one line of its CHOICE section active, and run `python make_main.py`.

## Calibrate the timing once

Delays and sample rates are counted in CPU clock ticks, and the library does not know your real CPU clock.
The default is 30 MHz, which may be wrong for your setup. Fix it once:

1. Generate and run the calibration program: `python -m vsk6748 gen calibration -o main.c`.
   LED1 stays on for "10 seconds" (by the assumed clock).
2. Time one "on" period with a stopwatch, for example 12.5 s.
3. Run `python -m vsk6748 calibrate 30000000 10 12.5`. It prints the real clock (here `24000000`).
4. Pass it everywhere: `vsk.blink(cpu_hz=24_000_000)`, or `cpu_hz=` on any preset or `Sketch`.

## Ready-made presets

Every function returns a `Sketch`. Call `.write("main.c")` to create the file
(it also prints warnings and notes, for example when the kit files are needed).
`cpu_hz` is accepted by all of them (default `30_000_000`).

### LEDs and DIP switches (no kit files needed)

| Function | What it does |
|---|---|
| `blink(led=1, on_ms=1000, off_ms=1000)` | one LED (1 to 8) on and off |
| `chase(on_ms=300, off_ms=300)` | each LED turns on then off, LED1 to LED8 |
| `knight_rider(step_ms=80)` | one LED sweeps back and forth |
| `switch_to_led()` | LED n copies DIP switch n |
| `binary_counter(step_ms=500)` | the 8 LEDs count in binary |
| `calibration(seconds=10)` | for [timing calibration](#calibrate-the-timing-once) |

### DAC and ADC (need the kit files)

| Function | What it does |
|---|---|
| `dac_wave(kind="sine", freq=1000, samples=64, amplitude=2047, offset=2048)` | `kind` is `sine`, `sawtooth`, `square` or `triangle`, on **DAC1** |
| `adc_to_dac()` | ADCLOOP: the signal on **ADC1 (CH1)** appears on DAC1 |

Values are 12-bit (0 to 4095, about 0 to 3.3 V). The DAC update rate is limited by the SPI transfer speed.
If `freq x samples` is too high the library prints a note, and the real frequency will be lower.

### Filters (need the kit files)

```python
vsk.fir("lowpass",  fs=8000, cutoff=1000, taps=45)          # lowpass, highpass, bandpass, bandstop
vsk.fir("bandpass", fs=8000, cutoff=(1000, 2000), taps=65)
vsk.iir("lowpass",  fs=8000, cutoff=1000, order=4)          # order 2 or 4 for LP/HP, 2 for BP/BS
vsk.iir("bandstop", fs=8000, cutoff=(800, 1600))
```

The filter is designed in Python (Hamming-window FIR, RBJ-biquad IIR) and then runs on the board:
**ADC1, filter, DAC1** at a fixed sample rate `fs`, timed with the CPU cycle counter, so `cpu_hz` must be
calibrated. The input is assumed to be centred on mid-scale (code 2048, about 1.65 V DC offset) and the
output is clamped to 0 to 4095.

Check a design on the PC before running it:

```python
h = vsk.fir_quantize(vsk.fir_design("lowpass", 8000, 1000, 45))
print(vsk.freq_response(h, [32768.0], 8000, 3000))          # gain at 3 kHz
```

`vsk.fir_reference(h, samples)` and `vsk.iir_reference(sections, samples)` compute exactly what the board
computes, so you can compare the DAC output with Python.

### Algorithm demos (plain C; results print in the CCS console; they also run in the CCS simulator)

```python
vsk.convolution([1, 2, 3, 4], [1, -1, 2])                        # linear
vsk.convolution([1, 2, 3, 4], [1, 1, 1], circular=True, n=4)
vsk.correlation([1, 2, 3, 4], [2, 0, 1])                         # cross-correlation
vsk.correlation([1, 2, 3, 4])                                    # auto-correlation
```

The expected answers are available in Python: `vsk.linear_convolution`, `vsk.circular_convolution`,
`vsk.cross_correlation`, `vsk.auto_correlation`.

### Audio codec (need the kit files; microphone on MIC IN, output on SKR OUT)

| Function | What it does |
|---|---|
| `audio_loopback(gain=3)` | mic to output jack (the lab manual's Mic and Speaker experiment) |
| `audio_tone(freq=1000, amplitude=12000, fs=48000)` | steady sine from the output jack |
| `mic_meter(divisor=400, loopback_gain=3)` | mic level on the 8 LEDs, plus a buffer `mic_buf` to graph in CCS |
| `audio_fsk(text="HELLO DSP", baud=200)` | sends text as audio tones to a PC line-in |

**Seeing the microphone without a speaker:** use `mic_meter()`. In CCS open *Tools, Graph, Single Time*, set the
start address to `mic_buf`, type to 16-bit signed integer, length 512.

**Board to PC data link:** run `audio_fsk("HELLO")`, connect SKR OUT to the PC line-in, then on the PC:

```bash
pip install numpy sounddevice
python -m vsk6748 fsk-rx --seconds 10      # prints: RECEIVED: HELLO
```

The receiver detects the codec's real sample rate on its own. Turn off noise suppression and audio
enhancements for that input in your operating system.

## Write your own Arduino-style sketch

```python
s = vsk.Sketch(cpu_hz=30_000_000)
s.add_globals("int count = 0;")
s.add_setup("pinMode(LED1, OUTPUT);")
s.add_loop("digitalWrite(LED1, count++ & 1); delay(500);")
s.write("main.c")
```

Or put `setup()` and `loop()` in a text file (any extension, for example `my.ino`):

```c
void setup() { pinMode(LED1, OUTPUT); }
void loop()  { digitalWrite(LED1, HIGH); delay(1000); digitalWrite(LED1, LOW); delay(1000); }
```

```python
vsk.Sketch.from_file("my.ino").write("main.c")
```

`loop()` runs forever, like Arduino. Call `pinMode`, `ledsInit`, `switchesInit`, `kitInit` or `audioInit` in
`setup()`; the library warns if you forget.

### Functions you can use inside a sketch

| Group | Functions |
|---|---|
| always | `delay(ms)`, `delayMicroseconds(us)`, `millis()`, `cyclesNow()`, `cyclesWaitUntil(t)`, `printf(...)` |
| pins | `LED1`..`LED8`, `SW1`..`SW8`, `pinMode(pin, INPUT/OUTPUT)`, `digitalWrite(pin, HIGH/LOW)`, `digitalRead(pin)` |
| LED / switch helpers | `ledsInit()`, `switchesInit()`, `ledWrite(n, v)` (n = 1..8), `ledsWrite(mask8)`, `switchesRead()` |
| DAC / ADC | `kitInit()` first, then `dacWrite(0..4095)` and `adcRead()` |
| audio | `audioInit()` first, then `audioRead()`, `audioWrite(v)`, `audioWriteStereo(v)` |

### `Sketch(...)` options

| Option | Meaning |
|---|---|
| `cpu_hz` | CPU clock in Hz, used by all timing (default 30 MHz, calibrate it) |
| `kit` | `True`/`False` to force the DAC/ADC/audio layer; normally automatic |
| `gpio` | `True`/`False` to force the LED/switch layer; normally automatic |
| `pll=(0,48,1,0,1,11,5)` | seven numbers passed to the kit's `config_pll0`, as in the manual's filter experiments. This changes the CPU speed, so recalibrate `cpu_hz` |
| `audio_rx` | `"XBUF4"` (default, what the lab manual's code reads) or `"RBUF4"` (the receive-buffer name in the TI manual; try it if the microphone reads zero). For a preset: `s = vsk.mic_meter(); s.audio_rx = "RBUF4"` |

### What the generated `main.c` contains

A small board layer (only the parts your sketch uses), then your `setup()` and `loop()`, then a `main()` that
initialises the board, calls `setup()` once and `loop()` forever. Everything is in one file.

## Command line

| Command | What it does |
|---|---|
| `python -m vsk6748 list` | list all presets |
| `python -m vsk6748 info` | show what is supported and how well it is verified |
| `python -m vsk6748 gen <preset> [--param KEY=VALUE ...] [-o main.c]` | generate `main.c` from a preset |
| `python -m vsk6748 build my.ino [--cpu-hz N] [--kit] [-o main.c]` | wrap your own sketch file |
| `python -m vsk6748 calibrate <current_hz> <seconds_wanted> <seconds_measured>` | compute the real CPU clock |
| `python -m vsk6748 fsk-rx [--seconds N] [--wav file.wav]` | PC receiver for `audio_fsk` |

Example: `python -m vsk6748 gen fir --param kind=lowpass --param fs=8000 --param cutoff=1000 -o main.c`.
After `pip install` the same commands are available as plain `vsk6748 ...`.

## ADC and DAC support

**Supported: ADC channel 1 and DAC channel 1**, the channels the lab manual uses in every experiment.
`adcRead()` reads ADC1 (CH1) and `dacWrite()` writes DAC1, using the same calls as the manual's code.

**The kit's common files must be in your CCS project.** The SPI setup (`Spi_inti`) and the audio setup
(`MCASP_init`, `AIC3106_init`, `I2C_init`) live there; this library calls them but cannot replace them.

**Not supported:** DAC2 and ADC channels 2 and up. The manual only gives the command word for channel 1
("refer manual" for the others) and no part numbers, so guessing would be unsafe. With the board schematic or
the kit's common files this can be added.

## Running main.c in Code Composer Studio

1. Connect and power the kit. In your CCS target configuration (XDS100v2, TMS320C6748), *Test Connection* must succeed.
2. Create a CCS project: target *C674x Floating-point DSP, TMS320C6748*, template *Empty Project (with main.c)*.
3. **DAC, ADC and audio presets only:** add the kit's common files. Under *Project, Properties, Build, C6000 Compiler,
   Include Options* add the folder that contains `VSK_6748.h`, and put the kit's `.c` files (for example `evmc6748.c`)
   in the project. Do not also paste a whole lab-manual experiment listing, because it has its own `main()`.
4. Paste the generated code over `main.c`. **Build, Debug, Resume (F8).**
5. LED programs: watch the board. `printf` programs: open the CCS Console. Mic meter: LEDs and the `mic_buf` graph.

## What is verified and what is not

`python -m vsk6748 info` prints this table.

| Feature | Status | Note |
|---|---|---|
| 8 LEDs `LED1..LED8` | verified in documents | GPIO8[8..15]; bit order vs. the D52..D59 labels not verified |
| 8 DIP switches `SW1..SW8` | verified in documents | GPIO0[0..7]; ON may read 0 or 1 |
| `delay` / `millis` | tested on PC | needs a calibrated `cpu_hz` |
| DAC1 write (12-bit) | copied from the lab manual | needs the kit files; only DAC1 is documented |
| ADC1 (CH1) read (12-bit) | copied from the lab manual | needs the kit files; only CH1 is documented |
| FIR / IIR filters | tested on PC | 2048 DC offset assumed; sample rate set by cycle-counter timing |
| convolution / correlation | tested on PC | plain C, also runs in the CCS simulator |
| audio in/out | copied from the lab manual | needs the kit files; 16-bit samples and 48 kHz are assumptions |
| audio FSK to PC | tested on PC | the PC receiver decodes the generated samples |
| DAC2, ADC channels 2+ | not supported | command words are not in the manual |

* Register offsets, the GPIO8[8..15] and GPIO0[0..7] pin-mux fields, the PSC1 GPIO module and the SYSCFG kick keys
  match the TI TMS320C6748 Technical Reference Manual (SPRUH79C).
* The LED and switch pin mapping and all DAC/ADC/audio calls come from the VSK-6748 lab manual.
* **Not tested** on the real board or with the TI compiler.
* **Unverified assumptions:** LED order vs. the physical labels, DIP-switch polarity, the codec sample rate (48 kHz),
  the 16-bit audio sample format, and your actual CPU clock.

## Troubleshooting

| Problem | Try |
|---|---|
| Build error "redefinition of delay / millis / ..." | a name clashes with the kit's headers; open an issue with the name |
| Build error "cannot open VSK_6748.h" | add the kit's common folder to *Include Options* |
| Linker error "undefined reference Spi_inti / MCASP_init" | the kit's `.c` files are not in the project |
| Delays or sample rates are wrong | [calibrate](#calibrate-the-timing-once) |
| LEDs do not change | in CCS Memory Browser open `0x01E260B4` and see whether the value changes |
| Microphone samples are all 0 | `audio_rx="RBUF4"` (see `Sketch` options) |
| DAC frequency lower than asked | lower `freq` or `samples`; the SPI write is the limit |
| Filter output looks clipped or offset | the input must be centred around 1.65 V (code 2048) |
| CCS error -151 (SC_ERR_FTDI_OPEN) | USB or driver problem: try another cable or port, power-cycle the board, close other debug sessions, reinstall the XDS100 driver |

## Project layout and tests

```
src/vsk6748/     the library (sketch.py, presets, design.py, clayers.py, cli.py, fsk_rx.py)
tests/           43 tests; compile the generated C on the PC against fake hardware (needs gcc)
examples/        example scripts and Arduino-style sketches
make_main.py     edit one line, run, get main.c
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```
