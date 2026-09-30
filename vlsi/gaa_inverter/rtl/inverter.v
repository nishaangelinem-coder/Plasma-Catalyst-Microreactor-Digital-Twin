// inverter.v -- RTL for the GAA nanosheet inverter demonstrator.
// Synthesised by Cadence Genus onto the GAA3 standard-cell library (INV_GAA_X1).
`timescale 1ps/1fs
module inverter (
    input  wire a,   // input
    output wire y    // y = ~a
);
    assign y = ~a;
endmodule
