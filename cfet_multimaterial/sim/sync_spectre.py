"""Rewrite the device instance lines and design-variable defaults of the Spectre netlists
(netlists/spectre/*.scs) with the calibrated parameter set (data/calibrated_params.json),
so that the Cadence path and the ngspice path describe identical devices.
Run: python3 -m sim.sync_spectre
"""
import os, re, json, glob
from .platforms import DEVICES, PLATFORMS, PARAM_ORDER, INF

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAL = json.load(open(os.path.join(HERE, "data", "calibrated_params.json")))
DEV_RE = re.compile(r"^(\s*\w+\s*\([^)]*\)\s*)(gaa_n|gaa_p|sige_p|mos2_n|wse2_p|cnt_n|cnt_p|gan_n|gan_p)\b(.*)\\\s*$")


def fmt(v):
    return "1e9" if v == INF else f"{v:.6g}"


def full_params(dev):
    p = dict(DEVICES[dev]["params"]); p.update(CAL.get(dev, {})); return p


def main():
    for path in sorted(glob.glob(os.path.join(HERE, "netlists", "spectre", "*.scs"))):
        lines = open(path).read().split("\n"); out = []; i = 0; changed = 0
        pl = next((k for k in PLATFORMS if f"_{k}." in os.path.basename(path) or f"_{k}_" in os.path.basename(path)), None)
        while i < len(lines):
            ln = lines[i]; m = DEV_RE.match(ln)
            if m and i + 1 < len(lines) and ("N0=" in lines[i + 1] or "TNOM=" in lines[i + 1]):
                dev = m.group(2); first = m.group(3)
                passed = set(re.findall(r"\b([A-Z0-9]+)=", first))
                p = full_params(dev)
                rest = " ".join(f"{k}={fmt(p[k])}" for k in PARAM_ORDER if k not in passed)
                out.append(ln); out.append("    " + rest + "   // calibrated defaults (data/calibrated_params.json)")
                i += 2; changed += 1; continue
            if ln.startswith("parameters Lg=") and "VTHN=" in ln:
                # device design variables: take them from the platform's n/p devices
                if pl is None:
                    mm = re.search(r"tb_(\w+?)_idvg", os.path.basename(path))
                    if not mm:
                        out.append(ln); i += 1; continue
                    dev = mm.group(1)
                    pl = next(k for k, P in PLATFORMS.items() if dev in (P["n"], P["p"]))
                n, pp = full_params(PLATFORMS[pl]["n"]), full_params(PLATFORMS[pl]["p"])
                out.append(f"parameters Lg={fmt(n['L'])} NNSn={n['NNS']} NNSp={pp['NNS']} WNS={fmt(n['WNS'])} RSW={fmt(n['RSW'])} "
                           f"VTHN={fmt(n['VTH0'])} VTHP={fmt(pp['VTH0'])} MUN={fmt(n['MU0'])} MUP={fmt(pp['MU0'])}   // calibrated")
                i += 1; changed += 1; continue
            out.append(ln); i += 1
        if changed:
            open(path, "w").write("\n".join(out)); print(f"{os.path.basename(path)}: {changed} lines synced")


if __name__ == "__main__":
    main()
