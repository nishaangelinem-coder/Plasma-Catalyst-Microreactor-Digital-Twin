# Running the Cadence Flow in a VMware Virtual Machine

Practical guide for the ECE research group at Velalar College of Engineering and Technology, Erode, to run the Spectre/Virtuoso flow of the phononic ring oscillator project inside a VMware guest and push the results back into the paper pipeline. All paths are relative to the project root `phononic-ring-oscillator/`.

## 1. Overview and what runs where

| Layer | Role | Notes |
|---|---|---|
| Host | Windows 10/11 or Linux workstation running VMware Workstation Pro, or an ESXi server | Holds the git checkout and runs the Python/LaTeX paper pipeline (`sim/`, `paper/`) |
| Guest | RHEL 8, Rocky Linux 8 or AlmaLinux 8 | Runs Virtuoso IC6.1.8 or IC23.1, SPECTRE23, DRC/LVS/PEX tools and the PDK |
| License server | Inside the guest, or a separate always-on host | FlexLM `lmgrd` + `cdslmd` |

Cadence publishes a supported-platform matrix for each release. RHEL 8 derivatives are supported for IC6.1.8 and IC23.1, but check the matrix for the exact point release, kernel and glibc you install. Do not use Ubuntu or Fedora for the guest; the tools may start but Cadence will not support failures.

What runs in the guest: Verilog-A compilation, PSS/Pnoise/stb/tran/PVT/Monte Carlo, layout, DRC/LVS, extraction. What runs on the host: `sim/collect_cadence_results.py`, `sim/make_figures.py`, `pdflatex`, git commits.

## 2. VM sizing

Recommended settings in VMware Workstation Pro (VM > Settings) or the ESXi VM editor:

```text
vCPU               8 or more (Spectre +aps and Monte Carlo scale with cores)
RAM                32 GB recommended, 16 GB minimum
Disk               250 GB, thin provisioned, single file or split is fine
Hardware version   VMX-13 or newer (Workstation 14 / ESXi 6.5 or later)
3D acceleration    OFF (Display > Accelerate 3D graphics unchecked)
Nested virt        OFF (Processors > Virtualize Intel VT-x/EPT unchecked)
Network adapter    Bridged if the license server is on the campus LAN;
                   NAT if the license server runs inside the guest
Guest OS type      Red Hat Enterprise Linux 8 (64-bit)
```

3D acceleration causes Virtuoso canvas redraw problems and random hangs in the VM; the layout editor is fast enough with software rendering.

Take a snapshot after installing the guest OS and again after installing the Cadence tools and PDK (VM > Snapshot > Take Snapshot). Restoring a snapshot is faster than reinstalling a tool tree that has been corrupted by a partial InstallScape run.

## 3. Guest OS preparation

Install the OS with the "Server with GUI" or "Workstation" profile. Then:

```bash
sudo dnf install -y epel-release
sudo dnf install -y glibc.i686 libXp libXext libXtst libXi libXmu libXrender \
    motif openmotif ksh csh tcsh xorg-x11-fonts-* xorg-x11-server-Xvfb \
    redhat-lsb-core libnsl libnsl2 ncurses-compat-libs libpng12 \
    mesa-libGLU gcc make perl open-vm-tools open-vm-tools-desktop chrony
```

`libXp` and `openmotif` may come from EPEL or need to be downloaded as RPMs from the Rocky/Alma vault; `motif` is the in-distribution replacement for `openmotif` and satisfies Virtuoso.

Kernel, SELinux and firewall:

```bash
# SELinux: permissive is enough; enforcing works but needs extra labelling of the tool tree
sudo sed -i 's/^SELINUX=.*/SELINUX=permissive/' /etc/selinux/config
# Firewall: open FlexLM ports if the license server runs here (see section 5)
sudo firewall-cmd --permanent --add-port=27000-27009/tcp
sudo firewall-cmd --permanent --add-port=5280/tcp
sudo firewall-cmd --reload
```

User and group setup. Run the tools as an unprivileged user that belongs to a shared `cad` group so a second student can reuse the install:

```bash
sudo groupadd cad
sudo useradd -m -G cad,wheel cadence
sudo mkdir -p /opt/cadence /opt/pdk /opt/license
sudo chown -R root:cad /opt/cadence /opt/pdk /opt/license
sudo chmod -R 2775 /opt/cadence /opt/pdk /opt/license
```

`ulimit`: Spectre opens many files during PSS and Monte Carlo. Add to `/etc/security/limits.conf`:

```text
@cad   soft   nofile   65536
@cad   hard   nofile   65536
@cad   soft   stack    unlimited
```

Hostname stability for FlexLM. The license file is tied to the host ID, which is the MAC address of the first NIC. VMware regenerates MAC addresses when a VM is copied or moved. Pin it in the `.vmx` file with the VM powered off:

```text
ethernet0.addressType = "static"
ethernet0.address = "00:50:56:XX:XX:XX"
ethernet0.checkMACAddress = "false"
```

Use an address in the VMware static range `00:50:56:00:00:00` to `00:50:56:3F:FF:FF`. Also fix the hostname and map it in `/etc/hosts`:

```bash
sudo hostnamectl set-hostname cadvm.vcet.local
echo "127.0.1.1 cadvm.vcet.local cadvm" | sudo tee -a /etc/hosts
```

Time sync. FlexLM refuses to serve if the clock is wrong and PSS logs are hard to correlate without it:

```bash
sudo systemctl enable --now chronyd
chronyc tracking
```

## 4. Installing Cadence

Required products: Virtuoso (IC6.1.8 or IC23.1), SPECTRE23 or newer (includes the Verilog-A compiler, APS and XPS), one physical-verification tool (Cadence PVS or ASSURA, or Siemens Calibre), and Quantus QRC for extraction. Verilog-A compilation needs no separate product; Spectre's built-in `ahdl` compiler handles `veriloga/phononic_ring_resonator.va`.

Licences. Academic groups in India obtain Cadence through one of:

- The Cadence University Software Program (direct agreement between the college and Cadence; the college signs and nominates an administrator).
- Europractice (for institutions that are members).
- An existing institutional licence pool, for example a central licence server already run by the department or by a partner IIT/NIT.

Terms and fees are set per institution; this document does not state them. The outcome is a license file (`license.dat` or `.lic`) and InstallScape download credentials.

Install with InstallScape:

```bash
# as user cadence
mkdir -p /opt/cadence/installscape && cd /opt/cadence/installscape
tar xzf ~/Downloads/IScape*.tgz
./iscape/bin/iscape.sh          # GUI
# or headless:
./iscape/bin/iscape.sh -batch majorAction=Download releaseName=IC23.1 \
    archiveDirectory=/opt/cadence/archive
./iscape/bin/iscape.sh -batch majorAction=Install releaseName=IC23.1 \
    archiveDirectory=/opt/cadence/archive installDirectory=/opt/cadence/IC23.1
```

Repeat for SPECTRE23, QUANTUS and PVS. After each install run the `checkSysConf` script shipped under `<install>/share/patchData/` to confirm missing OS packages.

Point `cadence/scripts/env.sh` at the install:

```bash
export CDS_INST_DIR=/opt/cadence/IC23.1
export SPECTRE_HOME=/opt/cadence/SPECTRE23
export QUANTUS_HOME=/opt/cadence/QUANTUS
export PVS_HOME=/opt/cadence/PVS
export PDK_ROOT=/opt/pdk/scl180
export CDS_LIC_FILE=5280@cadvm.vcet.local
export LM_LICENSE_FILE=$CDS_LIC_FILE
export PATH=$CDS_INST_DIR/tools/bin:$CDS_INST_DIR/tools/dfII/bin:$SPECTRE_HOME/tools/bin:$QUANTUS_HOME/tools/bin:$PVS_HOME/tools/bin:$PATH
export CDS_Netlisting_Mode=Analog
export CDS_AUTO_64BIT=ALL
```

Create the project working directory and `cds.lib` (Cadence reads `cds.lib` from the directory where `virtuoso` is started):

```text
DEFINE basic        $CDS_INST_DIR/tools/dfII/etc/cdslib/basic
DEFINE analogLib    $CDS_INST_DIR/tools/dfII/etc/cdslib/artist/analogLib
DEFINE ahdlLib      $CDS_INST_DIR/tools/dfII/samples/artist/ahdlLib
INCLUDE $PDK_ROOT/cds.lib
DEFINE phononic_osc ./phononic_osc
```

A minimal `.cdsinit` in the same directory loads the PDK bindkeys and the ADE defaults; a `.cdsenv` sets the simulator:

```text
; .cdsenv
asimenv.startup   simulator   string   "spectre"
asimenv.startup   projectDir  string   "./simulation"
spectre.envOpts   simExecName string   "spectre +aps +mt"
```

## 5. License server

Two options. For a single VM used by one group, run the daemon inside the guest. If several machines share the licence, run it on a separate always-on Linux host (or a second small VM) and point the guests at it.

Inside the guest:

```bash
mkdir -p /opt/license && cp ~/license.dat /opt/license/
# edit the SERVER line so the hostname and host ID match this VM
# SERVER cadvm.vcet.local 005056xxxxxx 5280
# VENDOR cdslmd /opt/cadence/IC23.1/tools/bin/cdslmd port=5281
nohup /opt/cadence/IC23.1/tools/bin/lmgrd -c /opt/license/license.dat \
    -l /opt/license/lmgrd.log &
```

Pin the vendor daemon port (`port=5281` on the VENDOR line) so the firewall rule is deterministic; without it FlexLM picks a random port. Open `5280/tcp` and `5281/tcp` (or 27000-27009 if you keep the default server port).

Check status:

```bash
export CDS_LIC_FILE=5280@cadvm.vcet.local
/opt/cadence/IC23.1/tools/bin/lmstat -a -c $CDS_LIC_FILE
```

`lmstat` must list `cdslmd: UP` and the features (`Virtuoso_Schematic_Editor`, `Spectre_RF`, `Virtuoso_ADE_*`, `PVS_*` or `Calibre_*`). Add a systemd unit so the daemon starts at boot:

```ini
# /etc/systemd/system/cdslic.service
[Unit]
Description=Cadence FlexLM
After=network-online.target
[Service]
User=cadence
ExecStart=/opt/cadence/IC23.1/tools/bin/lmgrd -z -c /opt/license/license.dat
Restart=on-failure
[Install]
WantedBy=multi-user.target
```

For Calibre, Siemens uses its own vendor daemon (`mgcld`) and `MGLS_LICENSE_FILE`; keep it on a different port.

## 6. Getting the project into the VM

Keep the git repository as the single source of truth. Two ways to see it from the guest:

Shared Folders (VM > Settings > Options > Shared Folders, add the host checkout, enable "Always enabled"):

```bash
sudo dnf install -y open-vm-tools open-vm-tools-desktop
sudo systemctl enable --now vmtoolsd
sudo mkdir -p /mnt/hgfs
sudo vmhgfs-fuse .host:/ /mnt/hgfs -o allow_other,uid=$(id -u cadence),gid=$(id -g cadence)
# make it persistent
echo ".host:/  /mnt/hgfs  fuse.vmhgfs-fuse  allow_other,defaults  0 0" | sudo tee -a /etc/fstab
ls /mnt/hgfs/Plasma-Catalyst-Microreactor-Digital-Twin/phononic-ring-oscillator
```

Do not run Virtuoso directly on the shared folder. HGFS does not support file locking and the Cadence library manager will corrupt `.oa` files. Instead clone into a native filesystem inside the guest and use the shared folder only to move CSV results back:

```bash
cd ~/work
git clone <repo-url> Plasma-Catalyst-Microreactor-Digital-Twin
cd Plasma-Catalyst-Microreactor-Digital-Twin/phononic-ring-oscillator
source cadence/scripts/env.sh
```

Commit results from the guest if git credentials are set up there, or copy `cadence/results/*.csv` to the shared folder and commit from the host (section 10). Either way, results reach the paper only through a commit.

## 7. PDK installation, library and schematic

Unpack the PDK (SCL 180 nm from Semi-Conductor Laboratory, Chandigarh, is the natural choice for an Indian academic group; the PDK is released under NDA to the institution. TSMC or UMC 180 nm also work with the same flow). Place it at `$PDK_ROOT` and include its `cds.lib` as shown in section 4. Confirm the model file path and corner section names in the PDK documentation; the netlists in `cadence/netlists/` reference them through `design_values.scs` and must be edited to match.

Create the project library from the CIW: File > New > Library, name `phononic_osc`, attach to the PDK technology library.

Import the Verilog-A resonator as a cellview. Either:

```text
CIW > File > Import > Verilog-A
  Target library:  phononic_osc
  Verilog-A file:  veriloga/phononic_ring_resonator.va
```

or copy the file by hand:

```bash
mkdir -p phononic_osc/phononic_ring_resonator/veriloga
cp veriloga/phononic_ring_resonator.va phononic_osc/phononic_ring_resonator/veriloga/veriloga.va
```

then open the cell and let Virtuoso create the `veriloga` view. Create a `symbol` view (Create > Cellview > From Cellview, from `veriloga` to `symbol`) with pins `p1 n1 p2 n2` and set the CDF so the model parameters are editable from the schematic. Netlist once with ADE and confirm the `ahdl_include` line appears in `input.scs`.

Build the schematic `phononic_osc/ring_osc` from `cadence/netlists/design_values.scs`: every element value (bias currents, device widths, feedback caps, inductor values) is listed there with the same instance names as `ring_osc_tb.scs`. Keep instance names identical so OCEAN scripts and LVS netlists line up.

Inductors. The design needs two 29.8 nH port inductors and one 40 nH differential tank inductor, each with a Q target of 8 at 1 GHz. Options in order of preference:

1. PDK spiral inductors, if the PDK offers values this large with Q of 8 at 1 GHz. Most 180-nm PDK spiral libraries top out well below 30 nH; check the PDK inductor documentation.
2. Custom spirals simulated in EMX, Momentum or Sonnet, imported as an S-parameter or RLCK model. Expect a large area (several hundred micrometres per side) and a self-resonance frequency that must stay above about 3 GHz.
3. External inductors: 0402 wire-wound parts or bond-wire inductance. This removes area but adds pad parasitics and package variation, and the on-chip part of the design must be re-simulated with the package model. Note this trade-off in the paper if used.

Whichever option you choose, replace the ideal `inductor` instances in the schematic with the chosen model and record the choice in `cadence/results/notes.txt`.

## 8. Running the flow

Three ways to run, from the most interactive to the most reproducible:

ADE Assembler or Explorer: open `phononic_osc/ring_osc_tb`, set up PSS and Pnoise as below, run, and inspect. Use this to debug convergence. Save the state (Session > Save State) so it can be replayed.

Headless OCEAN (preferred for results that go into the paper):

```bash
source cadence/scripts/env.sh
ocean -nograph -replay cadence/ocean/run_pss_pnoise.ocn
ocean -nograph -replay cadence/ocean/run_stb.ocn
ocean -nograph -replay cadence/ocean/run_tran_startup.ocn
ocean -nograph -replay cadence/ocean/run_pvt_corners.ocn
ocean -nograph -replay cadence/ocean/run_montecarlo.ocn
# or everything:
bash cadence/scripts/run_all.sh
```

Each script writes CSV files into `cadence/results/`.

Bare Spectre on the netlists (fastest, no Virtuoso licence needed):

```bash
cd cadence/netlists
spectre +aps +mt=8 -format psfascii ring_osc_tb.scs -raw ../results/ring_osc_tb.raw
spectre +aps amp_openloop_tb.scs -raw ../results/amp_openloop_tb.raw
# or
bash ../scripts/run_spectre.sh ring_osc_tb.scs
```

PSS and Pnoise settings:

```text
pss  fund=1.00115G  method=shooting  tstab=60u  maxacfreq=20G  errpreset=conservative
     harms=10  saveinit=yes
pnoise  sweeptype=relative  relharmnum=1  start=100  stop=10M  dec=20
        noisetype=pmjitter  (use noisetype=timeaverage for the sideband form)
        maxsideband=10
stb  (on amp_openloop_tb.scs)  start=1M stop=10G  dec=20  probe=IPRB0
```

`tstab` must be at least 60 us. The loaded Q is 17 925, so the resonator energy settles with a time constant of Q/(pi f0), roughly 5.7 us, and the start-up itself takes several microseconds; shooting Newton will not find the periodic solution from a transient that is still growing. `maxacfreq` sets the number of time points per period; 20 GHz is enough for the tenth harmonic. For `stb`, the `iprobe` instance goes at the TIA input node, between the resonator port 2 output and the transimpedance amplifier, so the loop is broken where the impedance mismatch is smallest.

Typical runtimes on 8 vCPU, 32 GB:

| Run | Time |
|---|---|
| PSS (tstab 60 us, shooting) | 10 to 40 min |
| Pnoise (100 Hz to 10 MHz) | 5 to 15 min |
| stb | under 1 min |
| tran start-up (100 us) | 10 to 30 min |
| PVT corners (15 to 27 points) | several hours |
| Monte Carlo (200 points) | overnight |

The Verilog-A delay element and the high Q dominate; a plain CMOS LC oscillator would run ten times faster.

If PSS does not converge:

1. Increase `tstab` to 100 us or 150 us and set `tstabmethod=full` if available in your release.
2. Switch to `pss method=harmonicbalance harms=10` with `oscana=yes`. Harmonic balance tolerates the long settling because it does not integrate through it.
3. Run `run_tran_startup.ocn`, confirm the oscillation is steady, then set `pss ... ic=all readns=<tran final state>` or use `saveinit`/`readinit` so shooting starts from the settled transient.
4. Check that `oscana=yes`, the `p` and `n` nodes are set to the tank, and `fund` is within 1 % of the free-running frequency; a wrong `fund` guess is the commonest cause.
5. For the Verilog-A block, make sure the `$abstime` delay is modelled with `absdelay()` and not a `transition()` filter; the latter breaks the Jacobian.

## 9. Layout, DRC, LVS, PEX

Layout in Virtuoso Layout XL (Launch > Layout XL from the schematic). Floorplan guidance:

- Differential symmetry: mirror the TIA, buffer and tank about a vertical axis; route the two phases with equal length and identical via counts.
- Inductor keep-out: no metal, substrate contacts or devices within the PDK keep-out distance of the spiral (typically one inductor radius); route differential lines over the gap, not across the turns.
- Guard rings: deep n-well or p+ guard rings around the TIA input devices and around the bias network, tied to a quiet ground.
- IDT pads: the resonator ports `p1 n1 p2 n2` leave the chip to the SiN-on-LN die. Use the PDK RF pad cell, ground-signal-ground spacing, and keep the pad-to-TIA trace short; include the pad model in the extracted netlist.
- Decoupling: fill empty area with MOS or MIM capacitors on VDD, within the 1.8 V rating.

DRC and LVS:

```bash
bash cadence/scripts/run_drc.sh    # wraps pvs -drc or calibre -drc with the PDK rule deck
bash cadence/scripts/run_lvs.sh    # wraps pvs -lvs or calibre -lvs, compares to the CDL netlist
```

Edit the rule deck path and the CDL export command in these scripts for your PDK; the scripts expect the SCL 180 nm deck names by default. LVS must report `CORRECT` or a clean match before extraction is meaningful.

Extraction with Quantus QRC:

```bash
bash cadence/scripts/run_pex.sh    # qrc with the PDK QRC techfile, RC + coupling caps
```

Settings: `extraction_type rc`, `coupling_caps on`, reference node `gnd!`, output as a Spectre netlist or an `av_extracted` view. The TIA input node capacitance and the port-inductor self-capacitance are the quantities that move the oscillation frequency and loop gain the most, so keep coupling caps on even though it slows the run.

Re-run on the extracted view: in ADE change the config view from `schematic` to `av_extracted` (or include the extracted `.scs` in `ring_osc_tb.scs` in place of the schematic subcircuit) and replay `run_pss_pnoise.ocn` and `run_stb.ocn`. Record the post-layout frequency, phase noise at 1 kHz, 10 kHz, 100 kHz and 1 MHz offset, power, and loop-gain margin in `cadence/results/postlayout_summary.csv`; `collect_cadence_results.py` picks it up when present.

## 10. Collecting results back into the paper

```bash
# in the guest: copy results to the shared folder
cp cadence/results/*.csv /mnt/hgfs/Plasma-Catalyst-Microreactor-Digital-Twin/phononic-ring-oscillator/cadence/results/

# on the host, from the project root
python3 sim/collect_cadence_results.py     # writes paper/data/ and results/cadence_results.json
python3 sim/make_figures.py                # regenerates paper figures
make -C paper                              # pdflatex
git add cadence/results paper/data results/cadence_results.json paper/figures
git commit -m "Add Cadence PSS/Pnoise results from VM run"
git push
```

If git is configured in the guest, commit from there instead and skip the shared-folder copy. Do not commit `.raw` directories, `simulation/` or `.oa` libraries; they are large and already ignored.

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Licensed number of users already reached` or `Cannot connect to license server` | Wrong `CDS_LIC_FILE`, daemon not running, firewall, host ID changed | `lmstat -a -c $CDS_LIC_FILE`; check `lmgrd.log`; confirm MAC pin in `.vmx`; open 5280/5281 |
| `ERROR (SPECTRE-16081)` or `ahdl` compile error on `phononic_ring_resonator.va` | Wrong `ahdl_include` path, missing `disciplines.vams`, unsupported construct in old Spectre | Use an absolute path in `ahdl_include`; run `spectre -ahdlcheck file.va`; use SPECTRE23 or newer |
| Virtuoso window blank, `Xlib: extension "GLX" missing`, or fonts missing | 3D acceleration on, missing `xorg-x11-fonts-*`, no `motif` | Disable 3D acceleration; install fonts and motif; `xset q` to confirm font path |
| Virtuoso or layout editor sluggish | Too few vCPU, memory ballooning, 3D on, HGFS used as working dir | Reserve memory in VM settings; move work to a native disk; 8 vCPU |
| PSS fails: `Periodic steady state not found` | `tstab` too short, wrong `fund`, delay element not supported | Section 8 list; `tstab` 100 us; harmonic balance; start from transient |
| Pnoise shows no 1/f^3 region | PDK model lacks `kf`, `af`, `noia` flicker parameters, or they are zero | Check the model file; ask the PDK vendor for the noise-characterised model; note the limitation in the paper |
| `/mnt/hgfs` empty | `vmtoolsd` not running, Shared Folders disabled, `vmhgfs-fuse` missing | `systemctl status vmtoolsd`; re-enable in VM settings; mount by hand as in section 6 |
| `cdslmd` exits immediately | Vendor daemon path wrong or 32-bit libs missing | Fix VENDOR line path; install `glibc.i686` |
| OCEAN script cannot find results dir | Run from a different cwd than the script expects | Always run from the project root after `source cadence/scripts/env.sh` |

## 12. Checklist

```text
[ ] VM: 8 vCPU, 32 GB, 250 GB thin, VMX-13+, 3D off, nested virt off, NIC mode chosen
[ ] Snapshot after OS install
[ ] RHEL 8 derivative installed; packages from section 3 installed
[ ] MAC address pinned in .vmx; hostname fixed; chrony running
[ ] Cadence IC, SPECTRE23, Quantus, PVS/Calibre installed with InstallScape
[ ] Snapshot after tool install
[ ] License daemon running; lmstat shows cdslmd UP and all needed features
[ ] cadence/scripts/env.sh edited and sourced
[ ] Repository cloned to a native guest filesystem; Shared Folder mounted
[ ] PDK installed; cds.lib includes it; model paths in design_values.scs updated
[ ] phononic_osc library created; Verilog-A cellview and symbol (p1 n1 p2 n2) imported
[ ] Schematic built from design_values.scs; inductor option chosen and noted
[ ] run_stb.ocn passes (loop gain > 1, phase margin recorded)
[ ] run_tran_startup.ocn shows steady oscillation
[ ] run_pss_pnoise.ocn converges with tstab >= 60 us; CSVs in cadence/results/
[ ] PVT and Monte Carlo runs completed
[ ] Layout DRC clean, LVS CORRECT, QRC extraction done
[ ] Post-layout PSS/Pnoise recorded in postlayout_summary.csv
[ ] Results copied to host; collect_cadence_results.py, make_figures.py, make -C paper run
[ ] Committed and pushed
```
