#!/usr/bin/env python3
"""Generate FIR coefficients, a test stimulus, and a bit-exact golden reference.

Writes three hex files (16-bit two's complement, one value per line) into the
current working directory:
    coeffs.hex    - Q1.15 FIR coefficients
    stimulus.hex  - input samples
    expected.hex  - golden output, computed with the SAME integer arithmetic
                    as rtl/fir_accel.v so the testbench can check bit-accuracy.

Usage (writes into ./data):
    pip install numpy scipy
    cd data && python ../scripts/gen_coeffs.py
"""
import numpy as np
from scipy.signal import firwin

N_TAPS = 31
FS     = 28000.0     # 28 kHz - matches the GMR DAQ rate
FC     = 2000.0      # low-pass cutoff (Hz)
NSAMP  = 256         # number of test samples (must match the testbench)
QF     = 15          # Q1.15 fractional bits


def to_q15(x):
    q = np.round(np.asarray(x) * (1 << QF)).astype(np.int64)
    return np.clip(q, -32768, 32767)


# --- FIR coefficients (low-pass) ---
h_q = to_q15(firwin(N_TAPS, FC / (FS / 2.0)))

# --- stimulus: in-band 500 Hz tone + out-of-band 8 kHz tone ---
n   = np.arange(NSAMP)
x   = 0.45 * np.sin(2 * np.pi * 500.0 * n / FS) + 0.35 * np.sin(2 * np.pi * 8000.0 * n / FS)
x_q = to_q15(x)


# --- golden reference: integer math IDENTICAL to the RTL ---
def fir_fixed(x_q, h_q):
    N = len(h_q)
    dline = [0] * N
    out = []
    for xs in x_q:
        dline = [int(xs)] + dline[:-1]
        acc = sum(int(h_q[k]) * dline[k] for k in range(N))   # full precision
        acc = (acc + (1 << (QF - 1))) >> QF                   # round, arithmetic shift
        acc = max(-32768, min(32767, acc))                    # saturate to 16-bit
        out.append(acc)
    return out


y_q = fir_fixed(x_q, h_q)


def w16(path, vals):
    with open(path, "w") as f:
        for v in vals:
            f.write(format(int(v) & 0xFFFF, "04x") + "\n")     # 16-bit two's complement


w16("coeffs.hex",   h_q)
w16("stimulus.hex", x_q)
w16("expected.hex", y_q)
print("wrote coeffs.hex, stimulus.hex, expected.hex | NSAMP=%d N_TAPS=%d" % (NSAMP, N_TAPS))
