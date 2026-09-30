; streamout_virtuoso.il -- SKILL snippet: stream the Virtuoso cellview to GDSII
; Load in CIW:  load("streamout_virtuoso.il")
xstOut(
  ?libName        "GAA3_INV_LIB"
  ?topCell        "INV_GAA_X1"
  ?view           "layout"
  ?strmFile       "./INV_GAA_X1.gds"
  ?layerMap       "./gaa3.layermap"
  ?units          "micron"
  ?dbuPerUU       1000          ; 1 nm database unit
  ?case           "preserve"
  ?logFile        "./strmOut.log"
)
; Command-line equivalent (from the VMware guest shell):
;   strmout -library GAA3_INV_LIB -topCell INV_GAA_X1 -view layout \
;           -strmFile INV_GAA_X1.gds -layerMap gaa3.layermap -logFile strmOut.log
