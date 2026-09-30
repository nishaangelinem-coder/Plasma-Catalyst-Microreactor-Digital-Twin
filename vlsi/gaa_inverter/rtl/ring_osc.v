// ring_osc.v -- 11-stage ring oscillator for the GAA3 flow.
// A combinational loop is deliberately created; the (* dont_touch *) attributes and the
// Genus preserve settings in genus/synth_ro.tcl keep all eleven INV_GAA_X1 stages.
`timescale 1ps/1fs
module ring_osc #(parameter N = 11) (
    input  wire en,     // 1 = oscillate (gated through an AND on the loop-closing net)
    output wire out
);
    (* dont_touch = "true" *) wire [N:0] n;
    assign n[0] = n[N] & en;                  // loop closure with enable (odd inverting stages)
    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : stage
            (* dont_touch = "true" *) INV_GAA_X1 u_inv (.A(n[i]), .Y(n[i+1]));
        end
    endgenerate
    assign out = n[N];
endmodule
