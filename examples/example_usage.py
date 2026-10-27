"""Use the library from your own Python file. Run: python examples/example_usage.py"""
import vsk6748 as vsk

CPU_HZ = 30_000_000

vsk.blink(led=3, on_ms=250, off_ms=750, cpu_hz=CPU_HZ).write("main_blink.c")

s = vsk.Sketch(cpu_hz=CPU_HZ)                       # your own Arduino-style logic
s.add_setup("ledsInit();\nswitchesInit();")
s.add_loop("ledsWrite(switchesRead());")
s.write("main_switches.c")

vsk.dac_wave("triangle", freq=500, cpu_hz=CPU_HZ).write("main_dac.c")
vsk.fir("lowpass", fs=8000, cutoff=1000, taps=45, cpu_hz=CPU_HZ).write("main_fir.c")
vsk.iir("bandpass", fs=8000, cutoff=(800, 1600), cpu_hz=CPU_HZ).write("main_iir.c")

# check a filter design on the PC before running it on the board
h = vsk.fir_quantize(vsk.fir_design("lowpass", 8000, 1000, 45))
for f in (100, 1000, 3000):
    print("FIR gain at %4d Hz = %.3f" % (f, vsk.freq_response(h, [32768.0], 8000, f)))

vsk.convolution([1, 2, 3, 4], [1, -1, 2]).write("main_conv.c")
print("expected:", vsk.linear_convolution([1, 2, 3, 4], [1, -1, 2]))
vsk.audio_loopback(gain=3).write("main_audio.c")
