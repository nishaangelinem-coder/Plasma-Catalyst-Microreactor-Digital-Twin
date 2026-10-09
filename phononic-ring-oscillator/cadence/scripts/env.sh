#!/bin/bash
# env.sh -- Cadence environment for this project (edit the four paths once)
export CDS_INST_DIR=/opt/cadence/IC231            # Virtuoso install
export SPECTRE_HOME=/opt/cadence/SPECTRE231        # Spectre install
export MGC_HOME=/opt/mentor/calibre               # Calibre (optional; or use PVS)
export CDS_LIC_FILE=5280@license.vcet.ac.in       # FlexLM licence
export PDK_ROOT=/opt/pdk/scl180                   # PDK root
export PDK_MODEL_FILE=$PDK_ROOT/models/spectre/scl180.scs
export PDK_SECTION=tt
export PATH=$CDS_INST_DIR/tools/bin:$CDS_INST_DIR/tools/dfII/bin:$SPECTRE_HOME/tools/bin:$MGC_HOME/bin:$PATH
export PROJ_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
mkdir -p "$PROJ_ROOT/cadence/results"
echo "Cadence env loaded: PROJ_ROOT=$PROJ_ROOT  PDK=$PDK_MODEL_FILE ($PDK_SECTION)"
