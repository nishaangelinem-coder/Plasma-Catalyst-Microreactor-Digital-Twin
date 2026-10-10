"""Re-simulate one held-out subject of E4 (same random stream as run_dynamic.job_E4) and
save its traces: python experiments/save_trace.py --seed 11 --scenario S1 --device bedside"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, common
from p2pneo.fluence import FluenceModel
from p2pneo.subject import sample_head, scenario_hypothermia, scenario_intermittent_hypoxaemia
ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=11); ap.add_argument("--scenario", default="S1")
ap.add_argument("--device", default="bedside"); ap.add_argument("--hours", type=float, default=10.0); ap.add_argument("--minutes", type=float, default=45.0)
a = ap.parse_args()
fl = FluenceModel(common.TABLE); rng = np.random.default_rng(a.seed + 1000)
head = sample_head(rng, bone_range=(0.0, 0.08))
dev = common.make_devices(frame_s=10.0 if a.scenario == "S1" else 2.0)[a.device]
if a.scenario == "S1":
    dev.frame_s = 20.0; scen = scenario_hypothermia(rng, dt=20.0, hours=a.hours, head=head)
else:
    scen = scenario_intermittent_hypoxaemia(rng, dt=2.0, minutes=a.minutes, head=head)
res = common.run_sequence(fl, head, dev, scen, rng, ablations=(a.device == "bedside"))
trace = dict(t=res["t"], truth_so2=res["truth"]["so2"], truth_Tb=res["truth"]["T_b"], truth_Ts=res["truth"]["T_s"],
             truth_Tcore=res["truth"]["T_core"], truth_g=res["truth"]["g"], sd_so2=res["sd"]["so2"], sd_T=res["sd"]["T"],
             Ts_est=res["Ts_est"], g_est=res["g_est"], events=np.array(res["events"]),
             **{f"so2_{m}": v for m, v in res["so2"].items()}, **{f"T_{m}": v for m, v in res["T"].items()})
out = os.path.join(common.RES, f"E4_trace_{a.scenario}_{a.device}_seed{a.seed}.npz")
np.savez_compressed(out, **trace); print("wrote", out, "bone", round(head.bone, 3), "snr", round(res["snr"]))
