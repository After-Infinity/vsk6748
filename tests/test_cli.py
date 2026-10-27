import os
import subprocess
import sys
import tempfile
import unittest

import vsk6748 as v
from vsk6748.cli import main


class Cli(unittest.TestCase):
    def gen(self, *args):
        out = os.path.join(tempfile.mkdtemp(), "main.c")
        rc = main(list(args) + ["-o", out])
        self.assertEqual(rc, 0)
        with open(out) as f:
            return f.read()

    def test_gen_with_params(self):
        c = self.gen("gen", "fir", "--param", "kind=lowpass", "--param", "fs=8000",
                     "--param", "cutoff=1000", "--param", "taps=31")
        self.assertIn("FIR_N 31", c)
        self.assertIn("int main(void)", c)
        self.assertIn("FIR_N 51", self.gen("preset", "fir", "--param", "taps=51"))

    def test_list_values_and_strings(self):
        c = self.gen("gen", "convolution", "--param", "x=[1,2,3]", "--param", "h=[1,1]")
        self.assertIn("NX 3", c)
        c = self.gen("gen", "audio_fsk", "--param", "text=Hi")
        self.assertIn("FSK_LEN 2", c)

    def test_errors(self):
        with self.assertRaises(SystemExit):
            main(["gen", "nope"])
        with self.assertRaises(SystemExit):
            main(["gen", "blink", "--param", "wrong=1"])

    def test_build_from_file_and_calibrate(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "s.ino")
        with open(src, "w") as f:
            f.write("void setup() { pinMode(LED1, OUTPUT); }\nvoid loop() { digitalWrite(LED1, HIGH); delay(1); }\n")
        out = os.path.join(d, "main.c")
        self.assertEqual(main(["build", src, "-o", out, "--cpu-hz", "24000000"]), 0)
        self.assertIn("#define CPU_HZ 24000000u", open(out).read())
        self.assertEqual(main(["calibrate", "30000000", "10", "12.5"]), 0)

    def test_python_dash_m(self):
        r = subprocess.run([sys.executable, "-m", "vsk6748", "list"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("dac_wave", r.stdout)


if __name__ == "__main__":
    unittest.main()
