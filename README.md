# Real-Time DSP Accelerator (FIR) — Verilog / AXI4-Stream

A parameterized, fully pipelined fixed-point **FIR filtering accelerator** in Verilog, verified **bit-accurate** against a Python golden model and timing-closed in Xilinx Vivado. It is the real-time front-end conditioning stage for multi-channel sensor data — modeled on 18-channel, 28 kHz GMR fault-detection signals (the input side of an edge-AI fault classifier).

## Highlights

- Transposed-form FIR — **one output sample per clock**, latency 2 cycles
- **Q1.15** fixed-point MAC with rounding and saturation
- **AXI4-Stream** handshake (`tdata` / `tvalid` / `tready`)
- Self-checking **SystemVerilog** testbench vs. a Python golden reference (bit-accurate, 256 vectors)
- Fully parameterized: tap count, data width, accumulator width

## Results (Artix-7 `xc7a35t`)

| Metric | Value |
|---|---|
| Fmax | _fill from Vivado timing report_ MHz |
| DSP48 / LUT / FF | _fill from Vivado utilization report_ |
| Verification | bit-accurate, 256 vectors |

## Architecture

```
                       coeffs.hex (Q1.15)
                              |
                              v
  s_axis_tdata  --> x --+--[x h0]--(+)--reg--+--(+)--reg ... --> r0 --> round (Q2.30->Q1.15)
  (Q1.15, 16b)          +--[x h1]--------+    |                            + saturate
  s_axis_tvalid         +--[x hN-1]-----------+                                |
  s_axis_tready                                                                v
                                          m_axis_tdata (Q1.15) <-- output register
                                          m_axis_tvalid       <-- 2-stage valid pipe
```

## Repo layout

```
.
├─ rtl/         fir_accel.v          # the accelerator
├─ sim/         tb_fir_accel.sv      # self-checking testbench
├─ scripts/     gen_coeffs.py        # generates the .hex vectors below
├─ data/        coeffs.hex  stimulus.hex  expected.hex
├─ constraints/ fir_accel.xdc        # clock constraint for Vivado
└─ README.md
```

## Simulate online (no install)

1. Open https://edaplayground.com (free account).
2. Languages: **SystemVerilog/Verilog**. Simulator: **Aldec Riviera-PRO** or **Synopsys VCS**. Tick **Open EPWave after run**.
3. Paste `rtl/fir_accel.v` into the Design pane and `sim/tb_fir_accel.sv` into the Testbench pane.
4. Add three files and paste the contents of `data/coeffs.hex`, `data/stimulus.hex`, `data/expected.hex`.
5. Run. The log should print `PASS: all 256 samples bit-accurate`. In EPWave, view `s_tdata` vs `m_tdata` to see the 8 kHz tone suppressed.

## Simulate locally (Icarus Verilog)

```bash
cd data
iverilog -g2012 -o sim.out ../rtl/fir_accel.v ../sim/tb_fir_accel.sv
vvp sim.out
```

(Run from `data/` so `$readmemh` finds the `.hex` files.)

## Regenerate the vectors

```bash
pip install numpy scipy
cd data && python ../scripts/gen_coeffs.py
```

Edit `N_TAPS`, `FC`, or `NSAMP` in `scripts/gen_coeffs.py` to retune the filter (keep `NSAMP` in sync with the `localparam` in the testbench).

## Synthesize (Vivado)

1. Create an RTL project; add `rtl/fir_accel.v` and `data/coeffs.hex` as sources.
2. Part: `xc7a35tcpg236-1` (or any Artix-7). Set `fir_accel` as top.
3. Add `constraints/fir_accel.xdc`.
4. Run Synthesis → read **Report Timing Summary** (WNS) and **Report Utilization** (LUT/FF/DSP). Compute `Fmax = 1000 / (5.000 - WNS)` MHz.

## Future work

- Symmetric-coefficient folding to halve DSP usage (linear-phase FIR)
- 18-channel time-division multiplexing to share one MAC engine
- AXI4-Stream skid buffer for full back-pressure support
- Runtime-reloadable coefficients via an AXI4-Lite register port
