// nand2.v -- RTL of the two-input NAND demonstrator; Genus maps it onto NAND2_GAA_X1.
`timescale 1ps/1fs
module nand2 (
    input  wire a,
    input  wire b,
    output wire y      // y = ~(a & b)
);
    assign y = ~(a & b);
endmodule
