;; floorplan.il -- SKILL helper: creates the top-level layout cellview with the
;; inductor keep-out boxes and pad placeholders from LAYOUT_PLAN.md.
;; load("floorplan.il") in the CIW, then run  (pro_floorplan "ring_osc_lib")
procedure( pro_floorplan( lib @optional (cell "ring_osc_top") )
  let( (cv)
    cv = dbOpenCellViewByType( lib cell "layout" "maskLayout" "w" )
    ;; die outline 550 x 450 um
    dbCreateRect( cv list("prBoundary" "boundary") list(0:0 550:450) )
    ;; inductor keep-outs (edge spacing >= 50 um)
    foreach( box list( list(30:250 180:400) list(230:250 380:400) list(400:120 530:250) )
      dbCreateRect( cv list("NO_FILL" "drawing") box ) )
    ;; pads (70 um) along the top edge
    foreach( x list(40 130 230 320 410 480)
      dbCreateRect( cv list("PAD" "drawing") list(x:410 (x+70):480) ) )
    dbSave( cv ) dbClose( cv )
    printf( "floorplan written to %s/%s/layout\n" lib cell )
  ))
