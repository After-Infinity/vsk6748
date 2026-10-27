"""PC-side receiver for the VSK-6748 audio-FSK link.
Setup:  pip install numpy sounddevice
Usage:  vsk6748 fsk-rx                 # record 6 s from the default input and decode
        vsk6748 fsk-rx --measure      # (optional) CAL_MODE tone -> real codec sample rate; normal decoding auto-tunes
        vsk6748 fsk-rx --wav file.wav # decode a recording
Plug SKR OUT -> PC line-in (blue) or mic-in (pink). Turn OFF noise suppression / AGC / enhancements.
"""
import sys, argparse
import numpy as np

FS_DSP = 48000.0                 # sample rate the firmware ASSUMES (FS_HZ in the C file)
BAUD, F0, F1 = 200, 1000.0, 2000.0
PRE_SYNC = "10101010" * 2 + "01111110"   # 0xAA 0xAA 0x7E

def demod_stat(x, fs, os_=8, k=1.0):
    f0, f1, baud = F0*k, F1*k, BAUD*k
    spb = fs / baud
    win = int(round(spb))
    t = np.arange(win) / fs
    e0, e1 = np.exp(-2j*np.pi*f0*t), np.exp(-2j*np.pi*f1*t)
    starts = np.round(np.arange(0, len(x) - win, spb / os_)).astype(int)
    idx = starts[:, None] + np.arange(win)[None, :]
    seg = x[idx]
    return np.abs(seg @ e1) - np.abs(seg @ e0), os_

def decode(x, fs, k=1.0):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    stat, os_ = demod_stat(x, fs, 8, k)
    frames = []
    for p in range(os_):
        bits = "".join("1" if v > 0 else "0" for v in stat[p::os_])
        pos = bits.find(PRE_SYNC)
        while pos != -1:
            q = pos + len(PRE_SYNC)
            def byte_at(i):
                b = bits[i:i+8]
                return int(b, 2) if len(b) == 8 else None
            n = byte_at(q)
            if n is not None and n <= 64:
                data = [byte_at(q + 8*(1+i)) for i in range(n)]
                chk = byte_at(q + 8*(1+n))
                if None not in data and chk is not None and sum(data) % 256 == chk:
                    msg = bytes(data)
                    if msg not in frames:
                        frames.append(msg)
            pos = bits.find(PRE_SYNC, pos + 1)
    return frames


def candidate_ks(x, fs, top=6):
    """Rank speed factors k (real codec rate / assumed rate) by how well both FSK tones
    (nominal 1 kHz and 2 kHz, scaled by k) show up in the recording."""
    x = np.asarray(x, dtype=np.float64); x = x - x.mean()
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1/fs)
    ks = 0.12 * (1.0025 ** np.arange(0, 1200))      # 0.12 .. ~2.4
    sc = np.array([min(spec[np.argmin(abs(f - k*F0))], spec[np.argmin(abs(f - k*F1))]) for k in ks])
    out = []
    for i in np.argsort(sc)[::-1]:
        if all(abs(ks[i]/k - 1) > 0.03 for k in out):
            out.append(ks[i])
        if len(out) >= top: break
    return out

def decode_auto(x, fs):
    for k0 in candidate_ks(x, fs):
        for dk in (0, -0.004, 0.004, -0.008, 0.008, -0.012, 0.012):
            k = k0 * (1 + dk)
            fr = decode(x, fs, k)
            if fr: return fr, k
    return [], 1.0

def measure(x, fs):
    x = np.asarray(x, dtype=np.float64); x = x - x.mean()
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1/fs)[np.argmax(spec)]
    print(f"Measured tone: {f:.1f} Hz (firmware intended {F1:.0f} Hz)")
    print(f"Real codec sample rate ~ {FS_DSP * f / F1:.0f} Hz -> set FS_HZ to this in the C file")

def record(seconds, fs=48000):
    import sounddevice as sd
    print(f"Recording {seconds}s ...")
    a = sd.rec(int(seconds*fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    return a[:, 0], fs

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--wav")
    ap.add_argument("--seconds", type=float, default=6)
    a = ap.parse_args(argv)
    if a.wav:
        import wave
        w = wave.open(a.wav); fs = w.getframerate(); ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
        x = x.reshape(-1, ch)[:, 0]
    else:
        x, fs = record(a.seconds)
    if a.measure:
        measure(x, fs)
    else:
        frames, k = decode_auto(x, fs)
        if frames:
            print(f"(codec speed factor {k:.3f} -> real sample rate ~ {FS_DSP*k:.0f} Hz)")
            for m in frames: print("RECEIVED:", m.decode("latin1"))
        else:
            print("No valid frame found. Check cable, input level and FS_HZ (run --measure).")


if __name__ == "__main__":
    main()
