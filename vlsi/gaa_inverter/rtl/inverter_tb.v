// inverter_tb.v -- self-checking testbench for RTL and post-layout gate-level netlist.
// Run (Xcelium):  xrun -timescale 1ps/1fs inverter.v inverter_tb.v
// Gate-level  :   xrun -timescale 1ps/1fs ../innovus/out/inverter_pnr.v inverter_tb.v \
//                    -v $GAA3_LIB/verilog/gaa3_stdcells.v -sdf_cmd_file sdf.cmd
`timescale 1ps/1fs
module inverter_tb;
    reg  a;
    wire y;
    integer errors = 0;

    inverter dut (.a(a), .y(y));

    initial begin
        a = 1'b0; #200;
        if (y !== 1'b1) begin $display("FAIL: a=0 y=%b", y); errors = errors + 1; end
        a = 1'b1; #200;
        if (y !== 1'b0) begin $display("FAIL: a=1 y=%b", y); errors = errors + 1; end
        repeat (8) begin a = ~a; #100; end
        if (errors == 0) $display("PASS: inverter truth table verified");
        $finish;
    end
endmodule
