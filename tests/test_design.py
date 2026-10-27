import math
import unittest

import vsk6748 as v


class FirDesign(unittest.TestCase):
    fs = 8000.0

    def gain(self, hq, f):
        return v.freq_response(hq, [32768.0], self.fs, f)

    def test_lowpass(self):
        hq = v.fir_quantize(v.fir_design("lowpass", self.fs, 1000, 45))
        self.assertAlmostEqual(self.gain(hq, 0), 1, delta=0.01)
        self.assertTrue(0.45 < self.gain(hq, 1000) < 0.55)       # -6 dB at the cutoff (window method)
        self.assertLess(self.gain(hq, 3000), 0.01)

    def test_highpass(self):
        hq = v.fir_quantize(v.fir_design("highpass", self.fs, 2000, 45))
        self.assertGreater(self.gain(hq, 4000), 0.98)
        self.assertLess(self.gain(hq, 200), 0.02)

    def test_bandpass_and_bandstop(self):
        bp = v.fir_quantize(v.fir_design("bandpass", self.fs, (1000, 2000), 65))
        self.assertGreater(self.gain(bp, 1450), 0.95)
        self.assertLess(self.gain(bp, 100), 0.05)
        bs = v.fir_quantize(v.fir_design("bandstop", self.fs, (1000, 2000), 65))
        self.assertLess(self.gain(bs, 1450), 0.05)
        self.assertGreater(self.gain(bs, 50), 0.95)

    def test_taps_forced_odd_and_bad_arguments(self):
        self.assertEqual(len(v.fir_design("lowpass", self.fs, 1000, 44)), 45)
        with self.assertRaises(ValueError):
            v.fir_design("lowpass", self.fs, 5000)               # above fs/2
        with self.assertRaises(ValueError):
            v.fir_design("weird", self.fs, 100)


class IirDesign(unittest.TestCase):
    fs = 8000.0

    @staticmethod
    def gain_of(secs, fs, f):
        m = 1.0
        for b0, b1, b2, a1, a2 in secs:
            m *= v.freq_response([b0, b1, b2], [1.0, a1, a2], fs, f)
        return m

    def test_lowpass_orders(self):
        for order, stop in ((2, 0.3), (4, 0.05)):
            s = v.iir_design("lowpass", self.fs, 1000, order)
            self.assertAlmostEqual(self.gain_of(s, self.fs, 20), 1, delta=0.02)
            self.assertAlmostEqual(self.gain_of(s, self.fs, 1000), 1 / math.sqrt(2), delta=0.01)   # -3 dB
            self.assertLess(self.gain_of(s, self.fs, 3500), stop)

    def test_highpass(self):
        s = v.iir_design("highpass", self.fs, 1000, 4)
        self.assertLess(self.gain_of(s, self.fs, 30), 0.01)
        self.assertAlmostEqual(self.gain_of(s, self.fs, 3900), 1, delta=0.1)

    def test_bandpass_bandstop(self):
        f0 = math.sqrt(800 * 1600)
        bp = v.iir_design("bandpass", self.fs, (800, 1600))
        self.assertGreater(self.gain_of(bp, self.fs, f0), 0.98)
        self.assertLess(self.gain_of(bp, self.fs, 60), 0.1)
        bs = v.iir_design("bandstop", self.fs, (800, 1600))
        self.assertLess(self.gain_of(bs, self.fs, f0), 0.01)
        self.assertGreater(self.gain_of(bs, self.fs, 60), 0.97)

    def test_bad_arguments(self):
        with self.assertRaises(ValueError):
            v.iir_design("bandpass", self.fs, 1000)              # needs (low, high)
        with self.assertRaises(ValueError):
            v.iir_design("lowpass", self.fs, 1000, order=3)


class Algorithms(unittest.TestCase):
    def test_linear_convolution(self):
        self.assertEqual(v.linear_convolution([1, 2, 3, 4], [1, -1, 2]), [1, 1, 3, 5, 2, 8])

    def test_circular_convolution_by_hand(self):
        self.assertEqual(v.circular_convolution([1, 2, 3, 4], [1, 1, 1], 4), [8, 7, 6, 9])

    def test_correlation(self):
        r = v.auto_correlation([1, 2, 3, 4])
        self.assertEqual(dict(r)[0], 30)
        self.assertEqual([b for _, b in r], [b for _, b in reversed(r)])
        self.assertEqual(v.cross_correlation([1, 2, 3, 4], [2, 0, 1])[0], (-2, 1))

    def test_against_numpy_if_available(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed")
        x, h = [1, 2, 3, 4], [1, -1, 2]
        self.assertEqual(v.linear_convolution(x, h), list(np.convolve(x, h)))
        n = 6
        xp, hp = [1, 2, 3, 0, 0, 0], [4, 5, 6, 7, 8, 0]
        ref = [int(round(z)) for z in np.fft.ifft(np.fft.fft(xp) * np.fft.fft(hp)).real]
        self.assertEqual(v.circular_convolution([1, 2, 3], [4, 5, 6, 7, 8], n), ref)


class Misc(unittest.TestCase):
    def test_calibration_maths(self):
        self.assertEqual(v.cpu_hz_from_stopwatch(30_000_000, 10, 12.5), 24_000_000)
        with self.assertRaises(ValueError):
            v.cpu_hz_from_stopwatch(30_000_000, 10, 0)

    def test_presets_listed(self):
        names = v.list_presets()
        for n in ("blink", "dac_wave", "fir", "iir", "convolution", "audio_fsk", "mic_meter"):
            self.assertIn(n, names)

    def test_argument_checks(self):
        with self.assertRaises(ValueError):
            v.blink(9)
        with self.assertRaises(ValueError):
            v.dac_wave("noise")
        with self.assertRaises(ValueError):
            v.Sketch(audio_rx="foo")
        with self.assertRaises(ValueError):
            v.Sketch(pll=(1, 2, 3))

    def test_lint_and_notes(self):
        s = v.Sketch(); s.add_loop("dacWrite(1);")
        self.assertTrue(any("kitInit" in w for w in s.lint()))
        s = v.Sketch(); s.add_loop("audioWrite(1);")
        self.assertTrue(any("audioInit" in w for w in s.lint()))
        s = v.Sketch(); s.add_loop("digitalWrite(LED1, HIGH);")
        self.assertTrue(any("pinMode" in w for w in s.lint()))
        self.assertIn(v.KIT_NOTE, v.dac_wave().all_notes())
        self.assertNotIn(v.KIT_NOTE, v.blink().all_notes())
        self.assertNotIn(v.KIT_NOTE, v.convolution([1], [1]).all_notes())

    def test_layers_only_when_used(self):
        self.assertNotIn("dacWrite", v.blink().render())
        self.assertIn("vsk_gpio_init", v.blink().render())
        conv = v.convolution([1, 2], [1, 1]).render()
        self.assertNotIn("vsk_gpio_init", conv)
        self.assertNotIn("dacWrite", conv)
        self.assertIn('#include "VSK_6748.h"', v.adc_to_dac().render())
        self.assertIn("MCASP->RBUF4", v.Sketch(audio_rx="RBUF4", kit=True).render())

    def test_dac_speed_warning(self):
        self.assertTrue(any("CPU cycles per DAC write" in n for n in v.dac_wave("sine", freq=100000).notes))

    def test_wave_tables(self):
        from vsk6748.design import _wave_table
        t = _wave_table("sine", 64, 2047, 2048)
        self.assertEqual((t[0], t[16], t[32], t[48]), (2048, 4095, 2048, 1))
        t = _wave_table("sawtooth", 64, 2047, 2048)
        self.assertEqual(t, sorted(t))
        t = _wave_table("square", 64, 2047, 2048)
        self.assertEqual(set(t), {4095, 1})


if __name__ == "__main__":
    unittest.main()
