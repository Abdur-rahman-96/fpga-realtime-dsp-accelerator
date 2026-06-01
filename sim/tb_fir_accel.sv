`timescale 1ns/1ps
//============================================================================
// tb_fir_accel.sv
// Self-checking testbench. Streams stimulus.hex through the DUT and compares
// every output sample to expected.hex (the Python golden reference).
// Prints "PASS" only if all samples are bit-accurate.
//============================================================================
module tb_fir_accel;
  localparam N_TAPS = 31;
  localparam DATA_W = 16;
  localparam NSAMP  = 256;          // must match gen_coeffs.py

  logic clk = 0, rst_n = 0;
  logic signed [DATA_W-1:0] s_tdata;  logic s_tvalid, s_tready;
  logic signed [DATA_W-1:0] m_tdata;  logic m_tvalid;

  fir_accel #(.N_TAPS(N_TAPS), .DATA_W(DATA_W)) dut (
    .clk(clk), .rst_n(rst_n),
    .s_axis_tdata(s_tdata), .s_axis_tvalid(s_tvalid), .s_axis_tready(s_tready),
    .m_axis_tdata(m_tdata), .m_axis_tvalid(m_tvalid), .m_axis_tready(1'b1)
  );

  always #5 clk = ~clk;             // 100 MHz

  logic signed [DATA_W-1:0] stim [0:NSAMP-1];
  logic signed [DATA_W-1:0] gold [0:NSAMP-1];
  integer in_i = 0, out_i = 0, errors = 0;

  initial begin
    $dumpfile("dump.vcd"); $dumpvars(0, tb_fir_accel);   // waveforms for EPWave
    $readmemh("stimulus.hex", stim);
    $readmemh("expected.hex", gold);
    s_tvalid = 0; s_tdata = 0;
    repeat (4) @(posedge clk);
    rst_n = 1;
  end

  // driver: one sample per clock
  always @(posedge clk) if (rst_n) begin
    if (in_i < NSAMP) begin s_tvalid <= 1; s_tdata <= stim[in_i]; in_i <= in_i + 1; end
    else                    s_tvalid <= 0;
  end

  // checker: compare each output as it streams out
  always @(posedge clk) if (rst_n && m_tvalid && out_i < NSAMP) begin
    if (m_tdata !== gold[out_i]) begin
      $display("MISMATCH idx=%0d got=%h exp=%h", out_i, m_tdata, gold[out_i]);
      errors = errors + 1;
    end
    out_i = out_i + 1;
    if (out_i == NSAMP) begin
      if (errors == 0) $display("PASS: all %0d samples bit-accurate", NSAMP);
      else             $display("FAIL: %0d mismatches", errors);
      $finish;
    end
  end

  initial begin #200000; $display("TIMEOUT"); $finish; end
endmodule
