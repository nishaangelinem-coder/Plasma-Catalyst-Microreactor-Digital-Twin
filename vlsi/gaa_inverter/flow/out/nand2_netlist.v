// nand2_netlist.v -- mapped by genus_ref.py onto gaa3_stdcells_tt_0p70v_25c
module nand2 (a, b, y);
  input a;
  input b;
  output y;
  NAND2_GAA_X1 g0 (.A(a), .B(b), .Y(y));
endmodule
