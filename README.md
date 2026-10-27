# vsk6748 - make programs for the VSK-6748 DSP kit with a few lines of Python

**You do not need to know C or the chip's registers.**
You write 1-3 lines of Python, run it, and it creates a ready-made `main.c` file.
You paste that file into Code Composer Studio (CCS), press the Debug button, and the board runs it.

> **Honest status:** the generated code is tested on a PC against a pretend board (43 automated tests).
> It has **not** been tested on a real board or with the TI compiler yet.
> If something behaves oddly on the real board, see [Troubleshooting](#7-troubleshooting).

---

## 1. The big picture (read this first)

```
  Your Python script  --->  main.c  --->  Code Composer Studio  --->  The board
   (my_program.py)        (a text file)      (Build, Debug, Run)     (LEDs blink, etc.)
        ^
   runs on your PC only,
   never on the board
```

Three things to remember:

1. **Python only writes a text file called `main.c`.** Python never runs on the board.
2. **You copy the text of `main.c` into your CCS project.** You do not copy any Python file into CCS.
3. Every time you change your script, you run it again and paste the new `main.c` into CCS.

---

## 2. What you need

| You need | Why |
|---|---|
| A PC with **Python 3.8 or newer** | to run the script. Check with `python --version` in a terminal |
| **Code Composer Studio (CCS)** and the kit plugged in by USB | to send the program to the board |
| The kit's own files (`VSK_6748.h`, `evmc6748.c`, ...) from your lab or CD | **only** for DAC, ADC, filters and audio. LEDs and switches do **not** need them |

You do **not** need to install anything with `pip`. See the next section.

---

## 3. What is in this folder?

You do not need to understand every file. Only the first two rows matter.

| Item | What it is | Do you touch it? |
|---|---|---|
| **`make_main.py`** | a ready-made script: pick one line, run it, get `main.c` | **Yes** |
| **your own script** (for example `my_program.py`) | the script you create, see step 4 | **Yes** |
| `examples/` | sample scripts you can copy ideas from | Look only |
| `src/` | the library's code (this is the "code-writing machine") | **No** |
| `tests/`, `docs/`, `pyproject.toml`, `.gitignore` | tests and project settings | **No** |
| `README.md`, `vsk6748-GUIDE.md` | documentation | Read only |

**Important:** your own scripts must live in this same folder, next to `src`.
That is how Python finds the library without installing it.

---

## 4. Your first program: blink an LED

This needs no extra kit files, so it is the best first test.

### Step 1 - Open a terminal in this folder

In VS Code: *Terminal -> New Terminal*. The prompt should show this project folder.

Check Python works:

```bash
python --version
```

If it says "command not found" on Windows, try `py --version` and use `py` instead of `python` everywhere below.

### Step 2 - Create your script

Create a new file called `my_program.py` **in this folder** (next to `src`) and paste this:

```python
import os, sys

# These 2 lines tell Python where the library is. Do not change them.
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "src"))

import vsk6748 as vsk

# ---- CHANGE ONLY THE NEXT LINE WHEN YOU WANT A DIFFERENT PROGRAM ----
program = vsk.blink(led=1, on_ms=1000, off_ms=1000)
# ----------------------------------------------------------------------

out = os.path.join(here, "main.c")
program.write(out)
print("DONE. main.c saved at:", out)
```

### Step 3 - Run it

```bash
python my_program.py
```

You should see `DONE. main.c saved at: ...` and a new file `main.c` appears in the folder.

### Step 4 - Put it into Code Composer Studio

1. Open `main.c` in VS Code, press `Ctrl+A` (select all), then `Ctrl+C` (copy).
2. In CCS, open the `main.c` of your CCS project, press `Ctrl+A`, then `Ctrl+V` (paste over everything).
3. Click **Build** (hammer icon), then **Debug** (bug icon), then **Resume** (press `F8`).

**LED 1 on the board now blinks once per second.**

Do not have a CCS project yet? See [Make a CCS project](#make-a-ccs-project-one-time).

---

## 5. Make it do something else

### Option A - pick another ready-made program (easiest)

In `my_program.py`, replace only the `program = ...` line, run the script again, and paste the new `main.c` into CCS.

**LEDs and switches (no kit files needed)**

| Line to use | What the board does |
|---|---|
| `vsk.blink(led=2, on_ms=500, off_ms=500)` | LED 2 blinks (LED number 1 to 8) |
| `vsk.chase(on_ms=300, off_ms=300)` | LEDs light up one after another |
| `vsk.knight_rider(step_ms=80)` | one light sweeps back and forth |
| `vsk.switch_to_led()` | LED n copies DIP switch n |
| `vsk.binary_counter(step_ms=500)` | the 8 LEDs count in binary |

**Signals (need the kit files, see [section 6](#6-programs-that-need-the-kits-own-files))**

| Line to use | What the board does |
|---|---|
| `vsk.dac_wave("sine", freq=1000)` | sine wave on DAC1 (also `"square"`, `"triangle"`, `"sawtooth"`) |
| `vsk.adc_to_dac()` | the signal on ADC1 comes out on DAC1 |
| `vsk.fir("lowpass", fs=8000, cutoff=1000)` | ADC1 -> low-pass filter -> DAC1 |
| `vsk.iir("lowpass", fs=8000, cutoff=1000, order=4)` | same, with an IIR filter |
| `vsk.audio_loopback(gain=3)` | microphone to the output jack |
| `vsk.audio_tone(freq=1000)` | steady tone from the output jack |
| `vsk.mic_meter()` | microphone loudness shown on the 8 LEDs |

**Maths demos (no kit files; results print in the CCS console)**

| Line to use | What it does |
|---|---|
| `vsk.convolution([1, 2, 3, 4], [1, -1, 2])` | linear convolution |
| `vsk.correlation([1, 2, 3, 4], [2, 0, 1])` | cross-correlation |

### Option B - write your own logic (Arduino style)

If you know Arduino, this will feel familiar. You write a **setup** (runs once) and a **loop** (repeats forever).
The code inside the triple quotes is C. Copy the pattern and change the lines.

Replace the `program = ...` line in `my_program.py` with:

```python
program = vsk.Sketch(cpu_hz=30_000_000)
program.add_setup("pinMode(LED1, OUTPUT); pinMode(LED2, OUTPUT);")
program.add_loop("""
    digitalWrite(LED1, HIGH);
    digitalWrite(LED2, LOW);
    delay(500);
    digitalWrite(LED1, LOW);
    digitalWrite(LED2, HIGH);
    delay(500);
""")
```

Example: LED 1 follows switch 1.

```python
program = vsk.Sketch()
program.add_setup("pinMode(LED1, OUTPUT); pinMode(SW1, INPUT);")
program.add_loop("digitalWrite(LED1, digitalRead(SW1));")
```

(The switch may be reversed, so if LED 1 is on when the switch is "off", use `!digitalRead(SW1)`.)

**Commands you can use inside `add_setup` / `add_loop`:**

| Command | Meaning |
|---|---|
| `pinMode(LED1, OUTPUT)` | make a pin an output. Do this in setup. For switches use `INPUT` |
| `digitalWrite(LED1, HIGH)` / `LOW` | turn an LED on / off |
| `digitalRead(SW1)` | read a DIP switch (0 or 1) |
| `delay(500)` | wait 500 milliseconds |
| `delayMicroseconds(100)` | wait 100 microseconds |
| `millis()` | milliseconds since the program started |
| `printf("x = %d\n", x)` | print text in the CCS console |
| `LED1` ... `LED8`, `SW1` ... `SW8` | the 8 LEDs and 8 DIP switches |
| `ledWrite(n, v)` / `ledsWrite(mask)` | set LED n, or all 8 LEDs at once (`ledsWrite(0xFF)`) |
| `switchesRead()` | read all 8 switches as one number |
| `kitInit()` then `dacWrite(0..4095)`, `adcRead()` | DAC / ADC (need kit files) |
| `audioInit()` then `audioRead()`, `audioWrite(v)` | audio codec (need kit files) |

Variables go in `add_globals`:

```python
program.add_globals("int count = 0;")
program.add_loop("count++; printf(\"count = %d\\n\", count); delay(1000);")
```

### Option C - write the sketch as a plain text file

Create `my.ino`:

```c
void setup() { pinMode(LED1, OUTPUT); }
void loop()  { digitalWrite(LED1, HIGH); delay(200); digitalWrite(LED1, LOW); delay(200); }
```

and use this line in `my_program.py`:

```python
program = vsk.Sketch.from_file(os.path.join(here, "my.ino"))
```

---

## 6. Programs that need the kit's own files

DAC, ADC, filters and audio use code that came with your kit (setup for the SPI chip and the audio codec).
This library cannot replace it, so these files must be inside your CCS project:

1. Find the kit's **common files** from your lab or CD: `VSK_6748.h`, `evmc6748.c` and the other `.c` files.
2. Copy the `.c` files into your CCS project folder.
3. In CCS: *Project -> Properties -> Build -> C6000 Compiler -> Include Options*, and add the folder that contains `VSK_6748.h`.
4. Paste the generated `main.c`. Do **not** also paste a whole lab-manual experiment, because that has its own `main()`.

Only **DAC1** and **ADC channel 1** are supported (the channels the lab manual uses).
Values are 12-bit numbers, 0 to 4095, which is about 0 V to 3.3 V.
Filters expect the input to be centred at about 1.65 V (value 2048).

### Make a CCS project (one time)

1. Connect and power the kit. In CCS, your target configuration (XDS100v2, TMS320C6748) must pass *Test Connection*.
2. *File -> New -> CCS Project*. Target: **TMS320C6748**. Template: **Empty Project (with main.c)**.
3. Now you can paste into its `main.c` as shown in step 4.

---

## 7. Troubleshooting

### Python and the terminal

| Problem | Fix |
|---|---|
| `python: command not found` | Windows: try `py`. Linux: install Python. Check with `python --version` |
| `ModuleNotFoundError: No module named 'vsk6748'` | your script is not in the same folder as `src`. Move it there |
| No `main.c` appears | look for the line `DONE. main.c saved at:` and open that exact path |
| `externally-managed-environment` (Arch Linux and others) when running `pip install .` | **You do not need pip.** Use the script method above. Never use `--break-system-packages` |

### On the board

| Problem | Fix |
|---|---|
| Build error: `cannot open VSK_6748.h` | add the kit's common folder in *Include Options* ([section 6](#6-programs-that-need-the-kits-own-files)) |
| Linker error: `undefined reference Spi_inti` or `MCASP_init` | the kit's `.c` files are not in your CCS project |
| Build error: `redefinition of delay / millis` | a name clashes with the kit's headers. Report the name |
| Delays are too long or too short | [calibrate the timing](#8-calibrate-the-timing-do-this-once) |
| LEDs do not change | in CCS open *Memory Browser* at address `0x01E260B4` and see whether the value changes |
| LED order looks wrong, or the switch is reversed | known unverified detail. Swap the LED number in your script, or use `!digitalRead(SW1)` |
| Microphone always reads 0 | add this after creating the program: `program.audio_rx = "RBUF4"` |
| DAC wave frequency is lower than asked | lower `freq` or `samples`. The SPI write speed is the limit |
| Filter output looks clipped or shifted | the input must be centred around 1.65 V (value 2048) |
| CCS error `-151` (SC_ERR_FTDI_OPEN) | USB or driver problem: try another cable or port, power-cycle the board, close other debug sessions, reinstall the XDS100 driver |

---

## 8. Calibrate the timing (do this once)

The library does not know your board's real CPU speed. It assumes 30 MHz, which may be wrong.
So "1 second" might really take 1.25 seconds. To fix it:

1. In `my_program.py` use: `program = vsk.calibration(seconds=10)`. Run it, paste into CCS, Debug, Resume.
2. LED1 turns on. Time with a stopwatch how long it stays on, for example 12.5 seconds.
3. In the terminal, from this folder (no install needed):

   ```bash
   PYTHONPATH=src python -m vsk6748 calibrate 30000000 10 12.5
   ```

   (Windows PowerShell: `$env:PYTHONPATH="src"; python -m vsk6748 calibrate 30000000 10 12.5`)

   It prints the real clock, here `24000000`.
4. Put that number in your program, for example `vsk.blink(led=1, cpu_hz=24_000_000)`.
   Every program accepts `cpu_hz=`.

---

## 9. Word list

| Word | Meaning |
|---|---|
| **Preset** | a ready-made program from this library, like `vsk.blink(...)` |
| **Sketch** | a program you write yourself with `setup` and `loop` (Arduino style) |
| **`main.c`** | the C file this library creates; the board's real program |
| **CCS** | Code Composer Studio, TI's program that builds and sends code to the board |
| **LED / DIP switch** | the 8 lights and 8 small slide switches on the board |
| **DAC** | turns a number into a voltage (output) |
| **ADC** | turns a voltage into a number (input) |
| **`cpu_hz`** | the CPU clock speed, used for all timing |
| **Terminal** | the text window where you type `python my_program.py` |

---

## 10. Advanced (optional)

### Command line instead of a script

Commands work after an install, or from this folder with `PYTHONPATH=src` in front:

```bash
PYTHONPATH=src python -m vsk6748 list                  # all presets
PYTHONPATH=src python -m vsk6748 info                  # what is verified on hardware
PYTHONPATH=src python -m vsk6748 gen blink --param led=1 --param on_ms=1000 --param off_ms=1000 -o main.c
PYTHONPATH=src python -m vsk6748 build my.ino -o main.c
PYTHONPATH=src python -m vsk6748 fsk-rx --seconds 10   # PC receiver for audio_fsk
```

### Real install (optional)

Not needed for the steps above. On systems like Arch Linux, use a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install .
```

After that you can drop the two `sys.path` lines and use plain `vsk6748 ...` commands.
Run `source .venv/bin/activate` again in each new terminal.

### More presets and options

- Audio over a cable to the PC: `vsk.audio_fsk("HELLO")`, then on the PC `pip install numpy sounddevice` and `python -m vsk6748 fsk-rx --seconds 10`.
- `Sketch(...)` options: `cpu_hz`, `kit`, `gpio`, `pll`, `audio_rx`. See `vsk6748-GUIDE.md`.
- Check a filter design on the PC before using it:

  ```python
  h = vsk.fir_quantize(vsk.fir_design("lowpass", 8000, 1000, 45))
  print(vsk.freq_response(h, [32768.0], 8000, 3000))   # gain at 3 kHz
  ```

### Run the tests

```bash
python -m unittest discover -s tests -v      # needs gcc
```

### Support status

| Feature | Status |
|---|---|
| 8 LEDs, 8 DIP switches | register addresses checked against the TI manual; LED order and switch polarity not verified on a real board |
| `delay`, `millis` | tested on PC; needs a calibrated `cpu_hz` |
| DAC1, ADC channel 1 | copied from the lab manual; needs the kit files |
| FIR / IIR filters | tested on PC |
| Convolution / correlation | tested on PC; also runs in the CCS simulator |
| Audio in/out | copied from the lab manual; 48 kHz and 16-bit samples are assumptions |
| DAC2, ADC channels 2+ | **not supported** (the manual does not give their command words) |
