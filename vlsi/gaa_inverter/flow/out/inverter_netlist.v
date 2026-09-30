// inverter_netlist.v -- mapped by genus_ref.py onto gaa3_stdcells_tt_0p70v_25c
module inverter (a, y);
  input a;
  output y;
  INV_GAA_X1 g0 (.A(a), .Y(y));
endmodule
