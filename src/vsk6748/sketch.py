"""The Sketch class: collects Arduino-style code and renders a complete main.c."""
import re
import sys

from .clayers import C_COMMON, C_TIMING, C_GPIO, C_KIT, C_INIT, C_MAIN

_DEFINES = re.compile(r'\bvoid\s+(setup|loop)\s*\(')


_GPIO_USE = re.compile(r'\b(LED[1-8]|SW[1-8]|VSK_PIN|pinMode|digitalWrite|digitalRead|'
                       r'ledWrite|ledsWrite|ledsInit|switchesInit|switchesRead)\b')


_KIT_USE = re.compile(r'\b(kitInit|dacWrite|adcRead|audioInit|audioRead|audioWrite|audioWriteStereo)\b')


KIT_NOTE = ("Needs the VSK-6748 common files in your CCS project (VSK_6748.h on the include path "
            "and the kit's .c files, e.g. evmc6748.c) - Step 8 of the lab manual.")


class Sketch:
    """Collects an Arduino-style sketch and renders a complete main.c.

    kit=True   -> also include the DAC / ADC / audio functions (needs the kit's common files)
    audio_rx   -> register read for microphone samples: "XBUF4" (what the lab manual's code does,
                  default) or "RBUF4" (the receive-buffer name in the TI TRM; try it if the mic reads 0)
    pll=(...)  -> 7 numbers passed to the kit's config_pll0(), e.g. (0,48,1,0,1,11,5) as the
                  manual's filter experiments do (changes the CPU speed: re-calibrate CPU_HZ)
    gpio=None  -> include LED/switch support only when the sketch uses it (True/False forces it)
    """

    def __init__(self, cpu_hz=30_000_000, title="sketch", kit=None, pll=None, gpio=None,
                 audio_rx="XBUF4"):
        if cpu_hz < 1_000_000:
            raise ValueError("cpu_hz looks too small (give it in Hz, e.g. 30_000_000)")
        self.cpu_hz = int(cpu_hz)
        self.title = title
        self.kit = kit            # None = auto (on when the sketch uses DAC/ADC/audio functions)
        self.pll = tuple(pll) if pll else None
        if self.pll and len(self.pll) != 7:
            raise ValueError("pll must be 7 numbers, as in config_pll0(a,b,c,d,e,f,g)")
        self.gpio = gpio
        if audio_rx not in ("XBUF4", "RBUF4"):
            raise ValueError('audio_rx must be "XBUF4" (as in the lab manual) or "RBUF4" (as in the TI TRM)')
        self.audio_rx = audio_rx
        self.notes = []
        self._globals = []
        self._setup = []
        self._loop = []

    # --- building a sketch ---
    def add_globals(self, code):
        """Variables / helper functions placed above setup()/loop()."""
        self._globals.append(code.strip("\n"))
        return self

    def add_setup(self, code):
        self._setup.append(code.strip("\n"))
        return self

    def add_loop(self, code):
        self._loop.append(code.strip("\n"))
        return self

    @classmethod
    def from_source(cls, source, cpu_hz=30_000_000, title="sketch", **kw):
        """Source is a complete Arduino-style file that defines setup() and loop()."""
        s = cls(cpu_hz, title, **kw)
        s.add_globals(source)
        return s

    @classmethod
    def from_file(cls, path, cpu_hz=30_000_000, **kw):
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_source(f.read(), cpu_hz, title=path, **kw)

    # --- assembling ---
    def _body(self):
        text = "\n\n".join(self._globals)
        have = set(m.group(1) for m in _DEFINES.finditer(text))
        parts = [text] if text else []
        if "setup" not in have:
            parts.append("void setup(void)\n{\n%s\n}" % self._indent("\n".join(self._setup)))
        if "loop" not in have:
            parts.append("void loop(void)\n{\n%s\n}" % self._indent("\n".join(self._loop)))
        return "\n\n".join(parts)

    @staticmethod
    def _indent(code):
        return "\n".join(("    " + ln) if ln.strip() else ln for ln in code.splitlines())

    def _uses(self):
        body = self._body()
        use_kit = self.kit if self.kit is not None else bool(_KIT_USE.search(body))
        use_gpio = self.gpio if self.gpio is not None else bool(_GPIO_USE.search(body))
        return use_gpio, use_kit

    def lint(self):
        """Return a list of human-readable warnings."""
        body = self._body()
        warns = []
        used_gpio = re.search(r'\b(digitalWrite|digitalRead|ledWrite)\s*\(', body)
        inited = re.search(r'\b(pinMode|ledsInit|switchesInit)\s*\(', body)
        if used_gpio and not inited:
            warns.append("digitalWrite/digitalRead/ledWrite used but pinMode()/ledsInit()/"
                         "switchesInit() never called - the pins will not be configured")
        if re.search(r'\bledsWrite\s*\(', body) and not re.search(r'\b(ledsInit|pinMode)\s*\(', body):
            warns.append("ledsWrite used but ledsInit() never called")
        if re.search(r'\bswitchesRead\s*\(', body) and not re.search(r'\b(switchesInit|pinMode)\s*\(', body):
            warns.append("switchesRead used but switchesInit() never called")
        if re.search(r'\b(dacWrite|adcRead)\s*\(', body) and not re.search(r'\bkitInit\s*\(', body):
            warns.append("dacWrite/adcRead used but kitInit() never called in setup()")
        if re.search(r'\b(audioRead|audioWrite|audioWriteStereo)\s*\(', body) and not re.search(r'\baudioInit\s*\(', body):
            warns.append("audioRead/audioWrite used but audioInit() never called in setup()")
        return warns

    # --- output ---
    def render(self):
        use_gpio, use_kit = self._uses()
        pll_line = ""
        if self.pll:
            pll_line = "        VSK_PLL_CALL(%s);\n" % ",".join(str(int(v)) for v in self.pll)
        kit_c = C_KIT.replace("@PLL_LINE@", pll_line).replace("@AUDIO_RX@", self.audio_rx)
        parts = ["/* %s - generated by the vsk6748 library for the VSK-6748 (TMS320C6748) */\n" % self.title,
                 C_COMMON.replace("@CPU_HZ@", str(self.cpu_hz)), C_TIMING]
        if use_gpio:
            parts.append(C_GPIO)
        if use_kit:
            parts.append(kit_c)
        parts.append(C_INIT.replace("@GPIO_INIT@", "    vsk_gpio_init();\n" if use_gpio else ""))
        parts.append("/* =================== end of board layer; your sketch follows =================== */\n")
        parts.append(self._body())
        parts.append(C_MAIN)
        return "\n".join(parts)

    def all_notes(self):
        _, use_kit = self._uses()
        out = list(self.notes)
        if use_kit and KIT_NOTE not in out:
            out.insert(0, KIT_NOTE)
        return out

    def write(self, path="main.c", quiet=False):
        if not quiet:
            for w in self.lint():
                print("warning:", w, file=sys.stderr)
            for n in self.all_notes():
                print("note:", n, file=sys.stderr)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.render())
        return path


def _csv(values, per_line=12):
    vals = [str(v) for v in values]
    lines = [", ".join(vals[i:i + per_line]) for i in range(0, len(vals), per_line)]
    return ",\n    ".join(lines)
