"""
collect_cadence_results.py -- merge Cadence (Spectre/OCEAN) outputs into the paper data.

Reads (if present) from cadence/results/:
    pnoise_nominal.csv      offset_Hz,L_dBcHz
    pss_summary.csv         f_osc_Hz,v_port1_peak_V,I_dc_A
    stb_loopgain.csv        f_Hz,T_dB,phase_deg (OCEAN ocnPrint format is also accepted)
    tran_port1.csv          time, v  (ocnPrint)
    pvt_corners.csv         corner,temp_C,vdd_V,f_osc_Hz,PN_1k_dBcHz,PN_100k_dBcHz,I_dc_A
    mc_resonator.csv        run,...,PN_100k_dBcHz
    postlayout_summary.csv  metric,prelayout,postlayout
Writes paper/data/cadence_*.csv and results/cadence_results.json.  make_figures.py
overlays the Cadence curves on the model curves when these files exist.
"""
import json, pathlib, re, sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "cadence" / "results"
DST = ROOT / "paper" / "data"
DST.mkdir(parents=True, exist_ok=True)


def read_ocn_or_csv(path):
    txt = path.read_text()
    rows = []
    for line in txt.splitlines():
        line = line.strip()
        if not line or line[0].isalpha() or line.startswith(";"):
            continue
        parts = re.split(r"[,\s]+", line)
        try:
            rows.append([float(x) for x in parts])
        except ValueError:
            continue
    return np.array(rows)


def main():
    out = {}
    if not SRC.exists():
        print("no cadence/results directory; nothing to collect"); return
    for name in ["pnoise_nominal", "pss_summary", "stb_loopgain", "tran_port1", "pvt_corners", "mc_resonator", "postlayout_summary"]:
        f = SRC / f"{name}.csv"
        if not f.exists():
            continue
        if name in ("pvt_corners", "postlayout_summary", "mc_resonator"):
            (DST / f"cadence_{name}.csv").write_text(f.read_text())
            out[name] = f.read_text().splitlines()[:50]
        else:
            d = read_ocn_or_csv(f)
            np.savetxt(DST / f"cadence_{name}.csv", d, delimiter=",")
            out[name] = d.tolist()[:200]
        print("collected", name)
    (ROOT / "results" / "cadence_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
