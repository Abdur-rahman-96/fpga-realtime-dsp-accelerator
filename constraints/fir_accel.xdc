## Real-time DSP accelerator - timing constraint
## Ask for 200 MHz; read WNS from "Report Timing Summary" and compute
## Fmax = 1000 / (5.000 - WNS_ns). If WNS is negative, raise the period.
create_clock -name clk -period 5.000 [get_ports clk]
