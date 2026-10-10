"""Build the Monte Carlo fluence/reflectance table (results/fluence_table.npz)."""
import sys, os, time, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from p2pneo import fluence
ap = argparse.ArgumentParser(); ap.add_argument("--nphot", type=int, default=150_000)
ap.add_argument("--nproc", type=int, default=4); a = ap.parse_args()
t = time.time()
out = os.path.join(os.path.dirname(__file__), "..", "results", "fluence_table.npz")
fluence.build_table(out, nphot=a.nphot, nproc=a.nproc)
print("table written", out, f"{time.time()-t:.0f} s")
