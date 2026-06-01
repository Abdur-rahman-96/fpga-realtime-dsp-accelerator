#!/usr/bin/env python3
# Cycle-accurate model of rtl/fir_accel.v + the tb driver/monitor timing.
# Reproduces the hardware register behaviour exactly (non-blocking semantics)
# and checks the streamed output equals expected.hex (the direct-form golden).
import sys, numpy as np

def s16(line):
    v = int(line.strip(), 16) & 0xFFFF
    return v - 0x10000 if (v & 0x8000) else v

def rd(path):
    return [s16(l) for l in open(path) if l.strip()]

h    = rd("coeffs.hex")
stim = rd("stimulus.hex")
gold = rd("expected.hex")          # signed
N    = len(h)
NSAMP= len(stim)
print(f"N_TAPS={N} NSAMP={NSAMP}")

def clamp(x): return max(-32768, min(32767, x))

# ---- state (mirrors the Verilog registers) ----
r = [0]*N
v1 = v2 = 0
y_q = 0
s_tvalid = 0; s_tdata = 0; in_i = 0     # tb driver regs
out_i = 0; errors = 0
outs = []

for k in range(NSAMP + 64):
    rst_n = 1 if k >= 4 else 0
    fire = (s_tvalid & 1) if rst_n else 0          # tready=1

    # ---- monitor: samples PRE-edge m_tvalid(v2)/m_tdata(y_q) ----
    if rst_n and v2 == 1 and out_i < NSAMP:
        got = y_q & 0xFFFF
        exp = gold[out_i] & 0xFFFF
        if got != exp:
            if errors < 8:
                print(f"  MISMATCH idx={out_i} got={got:04x} exp={exp:04x}")
            errors += 1
        outs.append(y_q)
        out_i += 1

    # ---- DUT next-state (from PRE-edge values) ----
    if not rst_n:
        r_n = [0]*N; v1n = 0; v2n = 0; y_qn = 0
    else:
        acc_r = (r[0] + (1 << 14)) >> 15           # round, arithmetic shift
        y_sat = clamp(acc_r)
        v1n, v2n, y_qn = fire, v1, y_sat
        if fire:
            r_n = [0]*N
            r_n[N-1] = s_tdata * h[N-1]
            for i in range(N-1):
                r_n[i] = r[i+1] + s_tdata * h[i]
        else:
            r_n = list(r)

    # ---- tb driver next-state ----
    if rst_n and in_i < NSAMP:
        s_tvalid_n, s_tdata_n, in_i_n = 1, stim[in_i], in_i + 1
    elif rst_n:
        s_tvalid_n, s_tdata_n, in_i_n = 0, s_tdata, in_i
    else:
        s_tvalid_n, s_tdata_n, in_i_n = s_tvalid, s_tdata, in_i

    # ---- commit ----
    r, v1, v2, y_q = r_n, v1n, v2n, y_qn
    s_tvalid, s_tdata, in_i = s_tvalid_n, s_tdata_n, in_i_n
    if out_i >= NSAMP:
        break

print(f"captured {len(outs)} outputs, errors={errors}")
if len(outs) == NSAMP and errors == 0:
    print("PASS: cycle-accurate RTL model is bit-accurate vs expected.hex")
else:
    print("FAIL"); sys.exit(1)

# ---- filter sanity: 500 Hz (in-band) should pass, 8 kHz (stop-band) should be cut ----
FS = 28000.0
y = np.array(outs[N:], dtype=float)            # skip warm-up
def tone_amp(sig, f):
    n = np.arange(len(sig))
    return 2.0/len(sig) * abs(np.sum(sig * np.exp(-1j*2*np.pi*f*n/FS)))
a500, a8k = tone_amp(y, 500.0), tone_amp(y, 8000.0)
print(f"output tone amplitude  500Hz={a500:8.1f}   8kHz={a8k:8.1f}   "
      f"stop-band rejection ~{20*np.log10(a500/max(a8k,1e-9)):.1f} dB")
