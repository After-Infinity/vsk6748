"""Generate main.c for each feature, compile it on the PC against fake hardware, check the behaviour."""
import math
import os
import re
import sys
import unittest

import vsk6748 as v
from helpers import run, needs_gcc, HERE

EXAMPLES = os.path.join(HERE, "..", "examples")


def close(a, b, tol):
    return abs(a - b) <= tol


@needs_gcc
class LedsAndSwitches(unittest.TestCase):
    def test_blink_pin_timing_and_setup(self):
        r = run(v.blink(3, 250, 750, 30_000_000), loops=3)
        self.assertEqual([x[1] for x in r["T"]][:6], [0x400, 0, 0x400, 0, 0x400, 0])   # LED3 = GPIO8[10]
        ts = [x[0] for x in r["T"]][:6]
        self.assertTrue(close(ts[1] - ts[0], 0.25, 0.005) and close(ts[2] - ts[1], 0.75, 0.005), ts)
        R = r["R"]
        self.assertEqual(int(R["DIR8"], 16), 0xFFFFFBFF)                  # only LED3 became an output
        self.assertEqual(int(R["PINMUX18"], 16), 0x88888811)
        self.assertEqual(int(R["PINMUX19"], 16), 0x11111188)
        self.assertEqual((R["KICK0"], R["KICK1"]), ("00000000", "00000000"))   # pin-mux registers re-locked
        self.assertEqual(int(R["MDCTL3"], 16) & 0x1F, 3)                  # GPIO clock enabled
        self.assertEqual(int(R["PINMUX1"], 16), 0x11111111)               # switch pins untouched

    def test_timing_follows_cpu_hz(self):
        r = run(v.blink(1, 1000, 1000, 24_000_000), loops=2)
        ts = [x[0] for x in r["T"]][:4]
        self.assertTrue(close(ts[1] - ts[0], 1.0, 0.01) and close(ts[2] - ts[1], 1.0, 0.01), ts)

    def test_chase_and_knight_rider(self):
        exp = []
        for i in range(8):
            exp += [1 << (8 + i), 0]
        self.assertEqual([x[1] for x in run(v.chase(100, 100))["T"]], exp)
        self.assertEqual([x[1] >> 8 for x in run(v.knight_rider(50))["T"]],
                         [1, 2, 4, 8, 16, 32, 64, 128, 64, 32, 16, 8, 4, 2])

    def test_switches_to_leds(self):
        r = run(v.switch_to_led(), in01="A5")
        self.assertEqual(int(r["R"]["OUT8"], 16), 0xA500)
        self.assertEqual(int(r["R"]["PINMUX1"], 16), 0x88888888)
        self.assertEqual(int(r["R"]["DIR01"], 16), 0xFFFFFFFF)            # switches stay inputs

    def test_binary_counter_and_millis(self):
        r = run(v.binary_counter(100), loops=5)
        self.assertEqual([x[1] >> 8 for x in r["T"]][-4:], [1, 2, 3, 4])
        s = v.Sketch(30_000_000); s.add_setup("ledsInit();"); s.add_loop("delay(2000);")
        self.assertTrue(1990 <= int(run(s)["R"]["MILLIS"]) <= 2100)

    def test_example_sketch_files(self):
        r = run(v.Sketch.from_file(os.path.join(EXAMPLES, "switches.ino")), in01="03")
        self.assertEqual(int(r["R"]["OUT8"], 16), 0x0300)
        for name in ("blink", "chase"):
            run(v.Sketch.from_file(os.path.join(EXAMPLES, name + ".ino")))


@needs_gcc
class DacAdc(unittest.TestCase):
    def test_waveforms(self):
        from vsk6748.design import _wave_table
        for kind in ("sine", "sawtooth", "square", "triangle"):
            r = run(v.dac_wave(kind, freq=1000, samples=64), loops=3, step=50)
            self.assertEqual(r["D"], _wave_table(kind, 64, 2047, 2048) * 3, kind)
            self.assertTrue(close(r["clk"] / 30e6, 0.003, 0.0002), r["clk"] / 30e6)     # 3 periods of 1 ms
            self.assertEqual((r["R"]["CALLS_SPI"], r["R"]["CALLS_USTIMER"]), ("1", "1"))

    def test_adc_to_dac(self):
        samples = [0, 1, 2047, 2048, 4095, 100, 3000]
        self.assertEqual(run(v.adc_to_dac(), loops=len(samples), adc=samples)["D"], samples)
        self.assertEqual(run(v.adc_to_dac(), loops=2, adc=[0xF123, 0x0ABC])["D"], [0x123, 0xABC])  # 12-bit mask

    def test_pll_option(self):
        r = run(v.adc_to_dac(pll=(0, 48, 1, 0, 1, 11, 5)), loops=1, adc=[5])
        self.assertIn("PLL 0 48 1 0 1 11 5", r["out"])


@needs_gcc
class Filters(unittest.TestCase):
    fs = 8000.0
    N = 400
    sig = [int(round(2048 + 700 * math.sin(2 * math.pi * 500 * i / 8000.0)
                     + 700 * math.sin(2 * math.pi * 3000 * i / 8000.0))) for i in range(400)]

    def test_fir_matches_python_model_exactly(self):
        s = v.fir("lowpass", self.fs, 1000, 45)
        r = run(s, loops=self.N, adc=self.sig, step=20)
        self.assertEqual(r["D"], v.fir_reference(s.coefficients, self.sig))
        self.assertTrue(close(r["clk"] / 30e6, self.N / self.fs, 0.002))      # paced at fs

    def test_fir_removes_high_tone_keeps_low_tone(self):
        r = run(v.fir("lowpass", self.fs, 1000, 45), loops=self.N, adc=self.sig, step=20)
        want = [2048 + 700 * math.sin(2 * math.pi * 500 * (i - 22) / self.fs) for i in range(100, self.N)]  # 22-sample delay
        self.assertLess(max(abs(a - b) for a, b in zip(r["D"][100:], want)), 120)

    def test_iir_matches_python_model(self):
        for kind, cut, order in (("lowpass", 1000, 4), ("highpass", 2000, 2),
                                 ("bandpass", (400, 700), 2), ("bandstop", (2500, 3500), 2)):
            s = v.iir(kind, self.fs, cut, order=order)
            r = run(s, loops=self.N, adc=self.sig, step=20)
            ref = v.iir_reference(s.sections, self.sig)
            self.assertLessEqual(max(abs(a - b) for a, b in zip(r["D"], ref)), 2, kind)

    def test_output_is_clamped(self):
        r = run(v.iir("lowpass", self.fs, 3500), loops=100, adc=[0] * 50 + [4095] * 50, step=20)
        self.assertTrue(min(r["D"]) >= 0 and max(r["D"]) <= 4095)


@needs_gcc
class Demos(unittest.TestCase):
    def printed(self, r, prefix):
        return [(int(a), int(b)) for a, b in re.findall(r"^%s\[(-?\d+)\] = (-?\d+)$" % prefix, r["out"], re.M)]

    def test_convolution(self):
        x, h = [1, 2, 3, 4], [1, -1, 2]
        got = [b for _, b in self.printed(run(v.convolution(x, h)), "y")]
        self.assertEqual(got, v.linear_convolution(x, h))
        got = [b for _, b in self.printed(run(v.convolution([1, 2, 3, 4], [1, 1, 1], circular=True, n=4)), "y")]
        self.assertEqual(got, [8, 7, 6, 9])
        got = [b for _, b in self.printed(run(v.convolution([1, 2, 3], [4, 5, 6, 7, 8], circular=True, n=6)), "y")]
        self.assertEqual(got, v.circular_convolution([1, 2, 3], [4, 5, 6, 7, 8], 6))

    def test_correlation(self):
        got = self.printed(run(v.correlation([1, 2, 3, 4], [2, 0, 1])), "r")
        self.assertEqual(got, v.cross_correlation([1, 2, 3, 4], [2, 0, 1]))
        got = self.printed(run(v.correlation([1, 2, 3, 4])), "r")
        self.assertEqual(got, v.auto_correlation([1, 2, 3, 4]))


@needs_gcc
class Audio(unittest.TestCase):
    def test_loopback(self):
        mic = [100, -200, 300, -400, 500, -600]
        r = run(v.audio_loopback(gain=3), loops=len(mic), rx=mic)
        self.assertEqual(r["A"], [3 * m for m in mic])
        self.assertEqual(r["R"]["CALLS_AUDIO"], "1")

    def test_tone(self):
        r = run(v.audio_tone(1000, 12000, 48000.0), loops=4800)
        left, right = r["A"][0::2], r["A"][1::2]
        self.assertEqual(left, right)
        self.assertTrue(11900 < max(left) <= 12000)
        cycles = sum(1 for a, b in zip(left, left[1:]) if a < 0 <= b)
        self.assertTrue(99 <= cycles <= 101, cycles)                       # 100 cycles in 0.1 s

    def test_mic_meter(self):
        mm = v.mic_meter(divisor=400)
        mm.add_loop("(void)cyclesNow();")                                  # lets the fake timer log LED changes
        r = run(mm, loops=12000, rx=[0] * 4000 + [1000] * 4000 + [4000] * 4000, step=20)
        self.assertEqual([x[1] >> 8 for x in r["T"]], [0, 0b11, 0b11111111])

    def test_fsk_decodes_on_pc(self):
        try:
            from vsk6748 import fsk_rx
        except ImportError:
            self.skipTest("numpy not installed")
        r = run(v.audio_fsk("HELLO VSK-6748", fs=48000), loops=2)
        left = r["A"][0::2]
        self.assertEqual(left, r["A"][1::2])
        self.assertEqual(fsk_rx.decode([a / 32768 for a in left], 48000), [b"HELLO VSK-6748"])


if __name__ == "__main__":
    unittest.main()
