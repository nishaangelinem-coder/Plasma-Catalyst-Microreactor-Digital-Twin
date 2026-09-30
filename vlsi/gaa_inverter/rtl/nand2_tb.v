// nand2_tb.v -- exhaustive truth-table check for RTL and post-layout netlist.
`timescale 1ps/1fs
module nand2_tb;
    reg a, b; wire y; integer i, errors = 0;
    nand2 dut (.a(a), .b(b), .y(y));
    initial begin
        for (i = 0; i < 4; i = i + 1) begin
            {a, b} = i[1:0]; #200;
            if (y !== ~(a & b)) begin $display("FAIL: a=%b b=%b y=%b", a, b, y); errors = errors + 1; end
        end
        if (errors == 0) $display("PASS: NAND2 truth table verified");
        $finish;
    end
endmodule
