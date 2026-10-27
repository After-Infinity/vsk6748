"""What the library supports on the VSK-6748, and how well each item is verified.

Status values:
  verified-docs   - register values checked against the TI TRM (SPRUH79C) and the lab manual
  manual-code     - copied from the lab manual's own experiment code; needs the kit's common files
  tested-on-pc    - the generated C was compiled and run against fake hardware (not the real board)
  unverified      - an assumption; check it on your board
"""

SUPPORT = [
    # (feature, status, where the information comes from, note)
    ("8 LEDs LED1..LED8", "verified-docs", "lab manual Exp 1 + TRM pin mux", "GPIO8[8..15]; bit order vs. D52..D59 not verified"),
    ("8 DIP switches SW1..SW8", "verified-docs", "lab manual Exp 2 + TRM pin mux", "GPIO0[0..7]; ON may read 0 or 1"),
    ("delay / millis (cycle counter)", "tested-on-pc", "C674x TSCL", "set cpu_hz by stopwatch calibration"),
    ("DAC1 write (12-bit)", "manual-code", "lab manual DAC experiments", "needs kit files (Spi_inti); only DAC1 is documented"),
    ("ADC1 (CH1) read (12-bit)", "manual-code", "lab manual ADCLOOP + filter experiments", "needs kit files; only CH1 is documented"),
    ("FIR / IIR real-time filters", "tested-on-pc", "design in Python, loop modelled on the manual", "DC offset 2048 assumed; fs set by cycle-counter pacing"),
    ("convolution / correlation demos", "tested-on-pc", "plain C", "also runs in the CCS simulator"),
    ("audio codec in/out (MIC IN, SKR OUT)", "manual-code", "lab manual Exp 7", "needs kit files; 16-bit samples and 48 kHz are assumptions"),
    ("audio FSK link board -> PC", "tested-on-pc", "own design", "decoded on a PC from the generated samples"),
    ("DAC2 / ADC channels 2+", "unverified", "not in the manual", "command words unknown - not supported"),
    ("PLL / CPU clock setup", "manual-code", "config_pll0(...) call from the manual", "optional pll=(...) argument; clock value after it is unknown"),
]


def support_table():
    """Return the support table as printable text."""
    w = max(len(r[0]) for r in SUPPORT)
    lines = ["%-*s  %-14s  %s" % (w, "feature", "status", "note"), "-" * (w + 60)]
    for feat, status, _src, note in SUPPORT:
        lines.append("%-*s  %-14s  %s" % (w, feat, status, note))
    return "\n".join(lines)
