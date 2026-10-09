# Invention Disclosure (draft for the institutional IP cell)

**Title:** Integrated CMOS sustaining amplifier and co-design method for low-loss
phononic ring-resonator oscillators with impedance-recovering port interfaces and
electronic mode selection

**Inventor(s):** Dr. M. Nisha Angeline (Professor and Head, Dept. of ECE, Velalar
College of Engineering and Technology, Thindal, Erode) and co-inventors (to be listed).

**Status of the work:** modelled and simulated (Verilog-A, ngspice transistor level,
Cadence Spectre flow prepared). No fabricated prototype yet. Keep this document
confidential until a provisional application is filed; do not present at conferences
or post preprints before filing (Indian Patents Act, s. 29 to 34 on anticipation; a
12-month grace does not apply to one's own publication in India).

---

## 1. Field

Reference oscillators and frequency sources for RF, timing and sensing; monolithic or
hybrid integration of gigahertz phononic integrated circuits (PnICs) on lithium
niobate (LN) with complementary metal-oxide-semiconductor (CMOS) electronics.

## 2. Problem

Phononic ring resonators on the new silicon-nitride-on-lithium-niobate (SiN-LN)
platform reach loaded quality factors near 18 000 at 1 GHz, but

1. their measured two-port insertion loss in a 50-ohm system is about 28 dB, of which
   only about 14 dB is intrinsic to the ring (drop-port transfer) while the other
   14 dB is IDT bidirectionality, taper loss and impedance mismatch;
2. their effective electromechanical coupling (motional over static capacitance) is
   of order 5 x 10^-6, so the parallel-resonance ("Pierce") oscillator topologies used
   for quartz, FBAR and MEMS resonators have an inductive window of only a few hertz
   and cannot be used;
3. the ring supports a comb of longitudinal modes spaced by the free spectral range
   (about 5.7 MHz) with almost equal loss, so a sustaining amplifier can start on the
   wrong mode or hop between modes;
4. existing demonstrations use bench amplifiers, phase shifters and 50-ohm
   interfaces, which forfeit the above loss and add noise.

## 3. Summary of the invention

A sustaining amplifier integrated in CMOS and a co-design method in which:

(a) each IDT port of the two-port phononic ring resonator is terminated by a shunt
inductor that resonates the IDT static capacitance C0 at the oscillation frequency, so
that the motional current of the resonator flows into a low-impedance current-mode
input stage and the driver stage does not supply the reactive current of C0; this
converts the 28-dB 50-ohm insertion loss into a loop loss of about 1.5 dB;

(b) the input stage is a differential common-gate (or common-base) cascode pair whose
bias current is fed through the centre tap of the port inductor of (a), so that the
noise of the bias current source appears as a common-mode signal and is rejected,
while the cascode isolates the stage-1 LC tank from the output conductance of the
input devices;

(c) the loop closes in series-resonance (transmission) mode: the ring is the only
frequency-selective element; the loop gain condition is a transimpedance condition
Z_T > R_m (motional resistance), not a negative-resistance condition;

(d) a varactor on the stage-1 LC tank, controlled by a calibration word, trims the
loop phase at the ring resonance; the same control selects the azimuthal mode of the
ring on which the loop oscillates, because adjacent modes of the ring differ in loop
phase by 180 degrees (half round-trip delay) and the in-phase competitors lie two
free spectral ranges away;

(e) the IDT finger-pair count N is chosen so that the first null of the IDT
transduction envelope sinc^2(N (f - f0)/f0) coincides with the in-phase competitor
modes at f0 +/- 2 FSR, i.e. N approximately equal to f0/(2 FSR); this raises the
mode-selection margin from below 2 dB to above 20 dB without any additional filter;

(f) the resonator is represented, for the co-design, by an extended
Butterworth-Van Dyke equivalent circuit augmented with a recirculating delay element
whose delay equals the ring round-trip time, so that the mode comb, the group delay
and the start-up dynamics are captured in the same compact model used for the
sustaining-amplifier phase-noise simulation.

## 4. Claims (draft, to be refined by the patent attorney)

1. An oscillator comprising: a two-port phononic ring resonator having a first
   interdigital transducer (IDT) and a second IDT, each IDT having a static
   capacitance C0; a first inductor connected across the first IDT and a second
   inductor connected across the second IDT, each inductor resonating with the
   respective C0 at the oscillation frequency; a differential current-mode input stage
   connected to the second IDT; at least one gain stage; and a driver stage connected
   to the first IDT, wherein the loop formed by the resonator and the stages satisfies a
   transimpedance condition at the series resonance of the resonator.
2. The oscillator of claim 1, wherein the second inductor has a centre tap through
   which the bias current of the input stage is supplied.
3. The oscillator of claim 1, wherein the input stage is a common-gate cascode pair
   loaded by an LC tank.
4. The oscillator of claim 3, wherein the LC tank includes a varactor whose control
   voltage sets the loop phase at the resonance of a selected azimuthal mode of the
   ring resonator.
5. The oscillator of claim 4, wherein changing the control voltage selects a different
   azimuthal mode of the ring resonator, the oscillation frequency changing by an
   integer multiple of the free spectral range.
6. The oscillator of claim 1, wherein the number of finger pairs N of at least one IDT
   satisfies 0.8 f0/(2 FSR) <= N <= 1.2 f0/(2 FSR), f0 being the oscillation
   frequency and FSR the free spectral range of the ring.
7. The oscillator of claim 1, wherein the phononic ring resonator comprises a
   patterned silicon-nitride waveguide on a lithium-niobate substrate.
8. The oscillator of claim 1, integrated in a bulk CMOS process, the resonator being
   flip-chip or wire bonded to the CMOS die, or fabricated above the CMOS metal stack.
9. A method of designing a sustaining amplifier for a phononic ring resonator,
   comprising: measuring the loaded, intrinsic and coupling quality factors and the
   50-ohm insertion loss of the resonator; deriving a motional resistance from these
   values and from the drop-port transfer of the ring; representing the resonator by
   an extended Butterworth-Van Dyke circuit augmented with a recirculating delay
   element of delay equal to the ring round-trip time; and sizing the input, gain and
   driver stages so that the loop transimpedance exceeds the motional resistance by a
   predetermined margin at the selected mode and is below it at the in-phase
   competitor modes.
10. A computer-readable compact model (Verilog-A) of a phononic ring resonator
    comprising the extended Butterworth-Van Dyke circuit and the recirculating delay
    element of claim 9, the delay element implemented as a delayed self-referencing
    state with round-trip amplitude and coupler transmission coefficients derived from
    the measured quality factors.

## 5. Advantages over prior art

| Prior art | Limitation | This invention |
|---|---|---|
| Bench oscillator around the SiN-LN ring (Ji et al., arXiv:2603.27711, 2026) | 50-ohm interfaces lose about 14 dB; external phase shifter; discrete amplifier noise | integrated, loss recovered, phase trim on chip |
| FBAR Pierce oscillators in CMOS (Otis and Rabaey 2003; Östman et al. 2006) | require k_t^2 of a few per cent; not applicable at k_eff^2 ~ 5e-6 | transmission-mode loop independent of k_eff^2 |
| SAW oscillators with external matching networks | discrete inductors, no mode-selection control | on-chip C0-resonating inductors with centre-tap bias; electronic mode selection |
| Delay-line and comb-mode oscillators in optics (OEOs) | optical components, watts of power | all-acoustic, milliwatt class |

## 6. Evidence available in the repository

* `veriloga/phononic_ring_resonator.va`: the compact model (claim 10).
* `sim/`: open-source reproduction of every number above (loss recovery, Pierce
  infeasibility, mode margin versus N, phase noise, Monte Carlo, temperature).
* `cadence/`: Spectre netlists and OCEAN scripts for PSS/Pnoise, stb, corners, MC.
* `paper/`: manuscript prepared for IEEE TCAS-I.

## 7. Suggested filing route

Indian provisional application (Form 1, Form 2 provisional specification) through
the institution, followed within 12 months by a complete specification and a PCT
application claiming priority. Prior-art search keywords: phononic ring resonator
oscillator; lithium niobate acoustic ring; transmission-mode sustaining amplifier;
common-gate transimpedance oscillator; centre-tapped inductor bias; mode selection
delay line oscillator; IDT sinc envelope mode suppression.
