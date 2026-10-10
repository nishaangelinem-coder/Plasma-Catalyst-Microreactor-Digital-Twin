# A Wearable/Bedside Photon-to-Phonon Monitor for Simultaneous Neonatal Cerebral Venous Oxygenation and Brain Temperature: Transfontanelle Photoacoustic Design Exploration and In-Silico Validation

**M. Nisha Angeline**

Department of Electronics and Communication Engineering, Velalar College of Engineering and Technology, Thindal, Erode, Tamil Nadu, India. E-mail: nishavlsidesign@gmail.com

*Manuscript prepared for submission to a Q1 journal in biomedical engineering (formatted after IEEE Transactions on Biomedical Engineering). This is an in-silico study: every quantitative result in this paper comes from a reproducible simulation; no phantom, animal or clinical measurement is reported.*

---

## Abstract

**Objective:** Neonates with hypoxic-ischaemic encephalopathy are treated with therapeutic hypothermia, yet the two quantities the therapy acts on, cerebral oxygenation and brain temperature, are not measured in the brain: near-infrared spectroscopy (NIRS) reports a mixed-compartment, extracerebrally contaminated regional saturation, and temperature is taken rectally. We design and evaluate a photoacoustic ("photon-to-phonon") monitor that reads both quantities from the superior sagittal sinus through the anterior fontanelle. **Methods:** Pulsed near-infrared photons at four wavelengths are converted by haemoglobin into ultrasonic phonons recorded by a 3-MHz transducer on the fontanelle. A joint extended Kalman filter fuses depth-gated multi-wavelength photoacoustic amplitudes (venous sO2 by spectral unmixing with a Monte-Carlo fluence model), the temperature dependence of the Grüneisen parameter of blood and of the speed of sound (differential pulse-echo shift), an on-probe reference absorber (coupling gain) and the probe thermistor. The design space (source class, wavelengths, centre frequency, ossification, optical and electronic heating, power budget) and the estimator are evaluated against a virtual neonate with hidden subject-specific anatomy, physiology and acoustics in two clinical scenarios (10-h therapeutic hypothermia with rewarming, and preterm intermittent hypoxaemia), against NIRS, linear and fluence-compensated unmixing, amplitude-only and echo-only thermometry, rectal and scalp thermometry, and ablations. **Results:** Over the open fontanelle the sinus receives 0.49 of the incident fluence at 800 nm; under a 0.1 W/cm² average-irradiance budget the sinus-gate signal-to-noise ratio per 10-s frame is 500 for a 10-mJ/cm² laser at 2.5 Hz, 100 for a laser-diode stack and 29 for an LED array, and under an average-power cap the lowest repetition rate that fills the single-pulse exposure limit maximises it. The 690/800/850/900-nm set gives a Cramér–Rao bound of 1.4 % on venous saturation. In static tests over 64 subject–states the filter recovers saturation with −0.1 ± 2.9 % limits of agreement (NIRS comparator +6.4 ± 10.3 %) and brain temperature within ±0.34 °C (rectal probe −0.52 °C). In the dynamic scenarios the median RMSE is 0.60 % (hypothermia) and 0.97 % (preterm, 2-s frames) for saturation and 0.38 °C and 0.10 °C for brain temperature, against 0.57 and 0.38 °C for the rectal probe, with 92–97 % of desaturations detected without false alarms, and the brain–scalp gradient is returned within 0.4 °C. The estimate tolerates ±30 % errors of the thermometric coefficients, a 16-fold noise increase and up to 1 mm of bone under the probe; the speed-of-sound coefficient and ossification beyond 1 mm are the dominant residual risks. A 1 °C scalp-heating limit corresponds to 50 mW/cm² of continuous irradiance, and a duty-cycled laser-diode patch runs 23 h on a 7.4-Wh battery. **Conclusion:** A fontanelle-coupled photoacoustic patch can track cerebral venous oxygenation and brain temperature simultaneously within the optical and thermal safety limits of a neonate, and a laser-diode wearable variant is feasible. **Significance:** The study provides a complete, open design and estimation framework and the quantitative targets for phantom, animal and clinical validation.

**Index Terms**— photoacoustics, neonatal monitoring, cerebral oximetry, brain temperature, therapeutic hypothermia, fontanelle, Grüneisen parameter, speed-of-sound thermometry, extended Kalman filter, wearable ultrasound, Monte Carlo light transport.

---

## I. Introduction

Therapeutic hypothermia (TH) is the only neuroprotective treatment with proven benefit for term neonates with moderate or severe hypoxic-ischaemic encephalopathy (HIE): cooling to a core temperature of 33.5 °C for 72 h followed by slow rewarming reduces death and disability [1–3]. Deeper or longer cooling does not help [4], and magnetic-resonance thermometry shows that the injured neonatal brain is systematically warmer than the rectum and that the gradient varies between infants and over time [5, 6]. The organ that the therapy targets is therefore controlled through a surrogate that can be off by up to a degree. Cerebral oxygenation is in a similar position. Regional cerebral oxygen saturation (rScO2) by near-infrared spectroscopy (NIRS) is widely used in neonatal intensive care [7], but it averages a mixed arterial/venous compartment, is contaminated by scalp and skull, differs by 10–15 % between devices and sensors [8], has an in-vivo precision of about 2.6 % [9], and treatment guided by it did not improve outcome in the largest trial to date [10, 11]. Preterm infants add a second use case: intermittent hypoxaemia, with desaturations lasting tens of seconds [12], under impaired cerebrovascular autoregulation [13].

Photoacoustic (optoacoustic) sensing converts photons into phonons: a nanosecond near-infrared pulse absorbed by haemoglobin heats the blood by millikelvins, the thermo-elastic expansion launches an ultrasonic wave, and the wave is recorded by an ultrasound transducer [14–16]. Because the initial pressure is proportional to the optical absorption, the spectrum of the signal gives the oxygen saturation of the blood that generated it [17], with ultrasonic rather than optical depth resolution. Because the conversion efficiency, the Grüneisen parameter, grows almost linearly with temperature in water-rich tissue and in blood, the amplitude also encodes temperature [18–22], and the speed of sound read by pulse-echo gives an independent thermometric channel [23–25]. Both properties have been demonstrated in the neonatal setting: optoacoustic monitoring of the superior sagittal sinus (SSS) through the anterior fontanelle has been performed in newborns [26] and validated against blood-gas oximetry in neonatal piglets [27], including with light-emitting-diode (LED) excitation [28], and transfontanelle photoacoustic imaging systems have been built and tested in sheep [29–31]. Stretchable ultrasound and photoacoustic patches have meanwhile reached deep-tissue haemodynamic monitoring in moving subjects and, in one case, haemoglobin and core-temperature imaging [32–36].

What is missing is a device-level design that brings these elements together for the neonate: a monitor that gives *venous cerebral* oxygen saturation and *brain* temperature at the same time, continuously, through the fontanelle, within the optical, acoustic and thermal exposure limits of a 3-kg infant, in a form that can be either a bedside probe or a battery-powered patch, and an estimation algorithm that separates the two quantities from the confounders that corrupt each of them in practice: optical fluence that changes with saturation (spectral colouring) [17, 37], the gel-coupling gain that changes with every movement, the amount of blood in the acoustic gate, the scalp temperature which differs from the brain by several degrees under a cooling cap, and sub-millimetre tissue displacement that shifts echoes as much as a degree of temperature would.

This paper makes the following contributions.

1. **A complete design-space exploration** of a fontanelle-coupled photon-to-phonon monitor: candidate source classes (LED array, pulsed laser-diode stack, compact laser) under the ANSI skin exposure limits and a neonatal thermal budget, wavelength-set selection by the Cramér–Rao bound, transducer centre frequency versus ossification and optical pulse width, echo-shift thermometry precision, and scalp and cortical heating by a Pennes bioheat model, with a wearable power budget.
2. **A joint estimator** that fuses depth-gated multi-wavelength photoacoustics, Grüneisen thermometry of blood at the isosbestic point, differential speed-of-sound thermometry, an on-probe reference absorber and the probe thermistor in an extended Kalman filter (EKF) with a Monte-Carlo fluence model and χ²-gated innovations, giving venous sO2, brain temperature, the brain–scalp gradient, the coupling quality and calibrated uncertainty every frame.
3. **A reproducible in-silico validation** against a virtual neonate whose anatomy, physiology, optics, acoustics and thermal coefficients are hidden from the estimator, in a 10-h therapeutic-hypothermia scenario with rewarming, desaturations, a seizure-like episode and movement artefacts, and in a preterm intermittent-hypoxaemia scenario, benchmarked against NIRS, classical unmixing, amplitude-only and echo-only thermometry, rectal and scalp thermometry, and four ablations, over held-out random subjects with paired statistics.

All code, readings and figures are released with the paper. The study is explicitly in-silico and ends with the validation plan it implies.

## II. Related Work and Gap

Table I summarises the approaches that bear on the problem.

**Table I. Existing approaches to neonatal cerebral oxygenation and brain-temperature monitoring and to photoacoustic sensing of the two quantities.**

| Family | Representative work | What it gives | Limitation for the neonatal use case |
|---|---|---|---|
| Continuous-wave NIRS cerebral oximetry (spatially resolved or multi-distance) | [7–11] | rScO2 of a mixed compartment, trend | 10–15 % inter-device offsets, extracerebral contamination, no depth selectivity, no temperature, no outcome benefit when used for treatment |
| Rectal / oesophageal / zero-heat-flux thermometry | [38, 39] | Core or skin-surface temperature | Brain–rectal gradient of 0.2–1 °C that varies with injury and cooling [5, 6] |
| MR-spectroscopy thermometry | [5, 6] | Absolute brain temperature | Snapshot only, transport of a cooled infant |
| Optoacoustic SSS oximetry | [26–28, 40] | Venous sO2 of the sagittal sinus, validated vs blood gas | Two wavelengths, no fluence model, no temperature, laboratory lasers or LED prototypes without coupling-gain control |
| Transfontanelle PA imaging | [29–31] | Images of haemorrhage and oxygenation | Cart-based tomographic systems, not continuous monitoring; no thermometry |
| Quantitative spectroscopic PA | [17, 37, 41, 42] | Fluence-corrected sO2 | Imaging-oriented; no temporal filtering or coupling control; not applied to the neonate |
| PA thermometry | [18–20, 22, 25] | Relative or absolute temperature from Γ(T) and c(T) | Assumes stable coupling and constant blood content; not combined with oximetry in one estimator |
| Low-cost PA sources | [43–48] | LED/laser-diode systems, cm-scale depth with averaging | Not evaluated under neonatal thermal limits; no design rule for the PRF/energy trade-off under an average-power cap |
| Wearable ultrasound / PA patches | [32–36] | Conformal arrays, haemoglobin and core temperature in adults | Not neonatal, not fontanelle-coupled, no joint oxygenation–temperature estimator with fluence model |
| Kalman fusion of physiological channels | [49–51] | Robust fusion of asynchronous noisy channels | Not applied to photoacoustic channels |

The gap is therefore not a single missing technology but the absence of (i) a joint model in which saturation, blood content, temperature of the blood, temperature of the scalp and coupling gain are all unknown and all enter the same photoacoustic amplitude; (ii) a second thermometric channel (speed of sound) with a different nuisance structure that makes the two temperatures identifiable; (iii) a design study that sets the source energy, pulse-repetition frequency, wavelengths and transducer frequency from the safety limits and the anatomy of the neonate rather than from what a laboratory laser happens to provide; and (iv) an evaluation protocol with hidden subject-specific parameters and clinically realistic disturbances, so that the quoted accuracy reflects structural model error and not only noise.

## III. System Concept and Design Space

### A. Measurement principle and probe

Fig. 0(a) shows the probe on the anterior fontanelle. The fontanelle is the natural acoustic window of the neonate, used daily for cranial ultrasound [52], and the superior sagittal sinus runs on the midline directly beneath it, 4–7 mm below the skin. The sinus is a 3–5-mm-wide blood-filled channel, so it is the strongest and best-defined photoacoustic absorber in the field of view, and its blood is cerebral venous blood, whose saturation reflects the balance between cerebral oxygen delivery and consumption more directly than a mixed regional saturation does [27, 40].

The probe contains (i) two near-infrared emitters on either side of (ii) an ultrasound element (3 MHz, 70 % bandwidth, 8 mm aperture for the bedside probe; a 6-mm capacitive-micromachined (CMUT) or piezo-polymer patch element for the wearable), (iii) a 1-mm acoustic stand-off pad that also carries (iv) a small black polymer *reference absorber* in the illuminated field, and (v) a thermistor at the pad–skin interface. Light at four wavelengths is time-multiplexed. Each frame (2–20 s) the device records the averaged photoacoustic A-line at every wavelength, one pulse-echo A-line, the reference-absorber amplitude and the thermistor value. From the A-lines it reads two depth gates placed by the pulse-echo line: a *scalp gate* at 0.3–1.5 mm and a *sinus gate* on the leading edge of the sinus. The sinus gate spectrum gives the venous saturation; the amplitude at the isosbestic wavelength (800 nm) is proportional to the Grüneisen parameter of blood, i.e. to its temperature [22]; the differential shift of the deep echo relative to the superficial echo measures the change of speed of sound in the tissue between them; the reference absorber measures the coupling gain; and the thermistor anchors the scalp temperature. The chain of Fig. 0(b) turns these into cerebral venous sO2, brain temperature, the brain–scalp gradient and a coupling-quality index with 95 % intervals.

### B. Source classes and the exposure-limited trade-off

Three source classes were considered (Table II): an LED array (100-ns pulses, 0.05 mJ/cm² per pulse on the skin [43, 45]), a pulsed laser-diode stack (80 ns, 0.5 mJ/cm² [47]) and a compact Q-switched or fibre laser with four lines (8 ns, 10 mJ/cm²). Two limits apply to every class. The ANSI Z136.1 skin limits for 700–1050 nm are a single-pulse maximum permissible exposure (MPE) of 20·C_A mJ/cm² (31.7 mJ/cm² at 800 nm, C_A = 10^{0.002(λ−700)}) and an average irradiance of 0.2·C_A W/cm² for exposures longer than 10 s [53]; we derate both by 2 for the neonate. The second limit is thermal: the Pennes model of Section IV shows that an insulating patch over a cooled infant should not deposit more than about 0.1 W/cm² of average irradiance if the scalp is to stay within 1 °C of its unperturbed value (Section V-F). With an average-power cap I_cap, per-pulse fluence F_0 and pulse-repetition frequency f_p satisfy F_0 f_p ≤ I_cap. Since the single-frame signal is proportional to F_0 and the noise falls as (f_p T)^{−1/2} after averaging over a frame of length T,

SNR ∝ F_0 √(f_p T) ≤ I_cap √T / √f_p,   (1)

so, under an average-power cap, *the lowest pulse-repetition frequency that still fills the single-pulse MPE maximises the SNR*. A 10-mJ/cm² laser at 2.5 Hz per wavelength, an LED array at 500 Hz per wavelength and a laser-diode stack at 50 Hz per wavelength all deposit 0.1 W/cm², but the laser's SNR advantage over the LED array is (10/0.05)·√(2.5/500) = 14 for the same frame. This rule, rather than the usual kilohertz LED repetition rates, drives the choices in Table II.

**Table II. Source and transducer options evaluated (four wavelengths, beam radius 5 mm, average irradiance 0.1 W/cm²).**

| Option | Pulse | Fluence per pulse (mJ/cm²) | PRF per wavelength (Hz) | Pulses per 10-s frame | Cost / form |
|---|---|---|---|---|---|
| LED array | 100 ns | 0.05 | 500 | 5000 | low, patch |
| Laser-diode stack | 80 ns | 0.5 | 50 | 500 | mid, patch |
| Compact laser (4 lines) | 8 ns | 10 | 2.5 | 25 | high, bedside cart |
| Single-element PZT, 8 mm, 3 MHz, 70 % | – | – | – | NEP 3 Pa single shot | bedside |
| Flexible PVDF patch, 6 mm | – | – | – | NEP 8 Pa | wearable |
| CMUT patch, 6 mm, 100 % bandwidth | – | – | – | NEP 1.5 Pa | wearable |

### C. Wavelengths, centre frequency and operating modes

Eight candidate wavelengths between 690 and 940 nm were screened by the Cramér–Rao bound of the venous saturation (Section V-A); 800 nm is always included because it is the isosbestic point at which the amplitude of the sinus gate depends on temperature and blood content but not on saturation [22]. The transducer centre frequency trades the sharpness of the sinus edge signal and the scalp–sinus separation against the frequency-dependent attenuation of any bone that has formed under the probe (Section V-B). Two operating modes result: a *bedside* mode (compact laser, single element, 10-s frames, mains-powered) and a *wearable* mode (laser-diode stack or LED array, CMUT patch, 10-s frames duty-cycled to 25 %, battery-powered); the preterm intermittent-hypoxaemia use case runs the bedside mode at 2-s frames.

## IV. Methods

### A. Virtual neonate (hidden truth)

**Head model.** The tissue under the probe is a layered half-space (Table III): scalp, fontanelle membrane (or bone when the fontanelle is partly ossified or the probe is off the window), cerebrospinal fluid (CSF), the sinus (whole blood) and brain parenchyma. Thicknesses and optical properties follow the neonatal values of Fukui et al. and Dehaes et al. [54, 55] and the review of Jacques [56]; whole-blood absorption uses the Prahl compilation of the oxy- and deoxy-haemoglobin extinction coefficients (Gratzer/Kollias data, as in [57]) with 2.3 mM haemoglobin and the whole-blood scattering of [58]; water absorption is from [59].

**Table III. Layered head model (nominal values; the virtual neonate randomises them as in Table IV).**

| Layer | Thickness (mm) | μ_a at 800 nm (cm⁻¹) | μ_s′ at 800 nm (cm⁻¹), exponent b | HbT (μM) | Water | c₀ (m/s), dc/dT (m/s/°C) | α₀ (dB/cm/MHz^y), y | Γ slope k_Γ (%/°C) |
|---|---|---|---|---|---|---|---|---|
| Scalp | 2.0 | 0.135 | 19, 1.2 | 40 | 0.55 | 1540, 1.3 | 0.70, 1.1 | 2.5 |
| Fontanelle membrane | 1.0 | 0.11 | 12, 1.0 | 10 | 0.60 | 1560, 1.3 | 1.5, 1.0 | 2.0 |
| Bone (if present) | 0–3 | 0.17 | 16, 0.6 | 15 | 0.30 | 2800, 0 | 12, 1.0 | 0.5 |
| CSF | 1.0 | 0.02 | 2.4, 0.5 | 0 | 0.99 | 1509, 2.4 | 0.002, 2.0 | 3.6 |
| Sinus (whole blood) | 3.0 | 4.2 | 7, 0.8 | 2300 | 0.80 | 1584, 1.5 | 0.20, 1.2 | 3.2 |
| Brain | ∞ | 0.15 | 6.5, 1.0 | 50 | 0.80 | 1546, 1.6 | 0.60, 1.1 | 3.0 |

**Light transport.** Fluence was computed with an MCML-type Monte Carlo code [60] written for this study (numba-compiled, Henyey–Greenstein scattering, Fresnel boundary at the skin, 10⁵ photon packets per configuration) that records, in addition to the absorbed energy per (r, z) bin, the first and second moments of the path length the contributing photons have travelled in every layer. The pencil-beam Green's functions were tabulated for 8 wavelengths × 4 bone thicknesses (0, 1, 2, 3 mm) × 3 scattering scales (0.8, 1.0, 1.2) × 3 sinus saturations (0.45, 0.65, 0.85) = 288 configurations, and the on-axis fluence of the flat-top 5-mm beam was obtained by integrating the pencil response over the beam. Any other state is reached by trilinear interpolation of the logarithmic fluence and of the partial path lengths across the grid, followed by the Beer–Lambert perturbation Φ(z) = Φ₀(z) exp(−Σ_j Δμ_{a,j} ⟨L_j(z)⟩ + ½ Σ_j Δμ_{a,j}² Var L_j(z)) for the residual change of absorption of layer j. The second-order term is used by the virtual neonate only; the estimator's model (Section IV-B) uses the first-order term and the population values of Table III, so that the two differ structurally. The model was verified against independent Monte Carlo runs at saturations between the grid nodes (Section V-A).

**Photon-to-phonon conversion and acoustics.** The initial pressure is p₀(z) = Γ(T(z)) μ_a(z) Φ(z) F₀, with Γ(T) = Γ₃₇[1 + k_Γ(T − 37 °C)], Γ₃₇ = 0.20, and the layer-specific slopes of Table III, which bracket the 2–4 %/°C reported for water-rich tissue and blood [18, 20–22]. Within the sinus p₀ is multiplied by the lateral fill factor f_v of the vessel within the aperture. For a laterally wide source and depths within the near field of the element, propagation is one-dimensional: the pressure at the probe is p(t) = ½ p₀(z = ct) [15], computed in the frequency domain with the layer-wise frequency-dependent attenuation α₀ f^y and sound speeds c_j(T) = c_{j,0} + k_{c,j}(T − 37 °C) of Table III [23, 61, 62], a 1-mm stand-off delay, the optical pulse spectrum (sinc of the pulse width, which penalises 100–300-ns LED and laser-diode pulses) and a Gaussian transducer band-pass. Noise is band-limited white noise with a single-shot in-band rms of the noise-equivalent pressure of Table II, scaled by the square root of the noise bandwidth and averaged over the pulses of the frame. The device DSP reads the mean Hilbert envelope in the two gates and estimates its own noise floor from the signal-free end of the A-line.

**Pulse-echo channel.** The pulse-echo A-line is synthesised with the same band-pass from three reflectors: the pad–skin interface, the scalp–membrane interface and a deep speckle window at 13–17 mm. The device cross-correlates each window with the first frame (parabolic sub-sample interpolation) and forms *differential* shifts Δτ_s (superficial segment) and Δτ_b (deep segment), which cancel the whole-line jitter produced by probe motion. A non-thermal nuisance (tissue pulsation and slow displacement: an Ornstein–Uhlenbeck process of 5 ns standard deviation and 10-min correlation time plus 1.5 ns white noise) is added to the deep echo by the virtual neonate.

**Reference absorber, thermistor and NIRS comparator.** The reference absorber returns g·(1 − 0.001(T_probe − 37)) with a single-shot SNR of 200, where g is the coupling gain. The thermistor reads the pad–skin interface, which the virtual neonate keeps 0.3–1.0 °C above the scalp dermis, with 0.1 °C noise. The NIRS comparator is an *empirical* model of a commercial cerebral oximeter, not a physics simulation: rScO2 = (1 − w)[0.75 sO2_v + 0.25 SaO2] + w sO2_scalp + b + ε, with extracerebral weight w ~ U(0.15, 0.35), device/sensor offset b ~ U(−6, +6) % [8] and ε of 2.6 % standard deviation per 10-s frame [9].

**Subjects and scenarios.** Each held-out subject draws the hidden parameters of Table IV. Scenario S1 (therapeutic hypothermia, 10 h, 20-s frames) cools the core from 37 to 33.5 °C with a 25-min time constant, holds it, and rewarms at 0.5 °C/h from 4 h; the brain is 0.2–0.8 °C warmer than the core with a gradient that grows with cooling [5], the scalp is 1–3 °C colder than the core (cooling cap and ambient), the venous saturation drifts around 68 % with two desaturations of 12–22 % lasting 1.5–4 min, a seizure-like episode at 6.5 h raises brain temperature by 0.4 °C, blood content by 8 % and saturation by 5 % for 15 min, movements occur about every 30 min and each reduces the coupling gain by 5–40 % with slow partial recovery. Scenario S2 (preterm intermittent hypoxaemia, 45 min, 2-s frames) contains twelve desaturations of 8–25 % lasting 20–90 s [12] at a stable temperature, with movements every ~7 min.

**Table IV. Hidden subject-specific parameters of the virtual neonate (uniform ranges).**

| Parameter | Range | Parameter | Range |
|---|---|---|---|
| Bone under probe (mm) | 0–0.8 (E3, E4); 0–3 (E5) | Scalp thickness (mm) | 1.6–2.4 |
| Scattering scale (all layers) | 0.8–1.2 | Background absorption scale | 0.7–1.3 |
| Scalp HbT (μM), sO2 | 28–52, 0.60–0.80 | Parenchymal HbT (μM) | 38–65 |
| Haematocrit scale of blood | 0.85–1.15 | Sinus fill factor f_v | 0.35–0.65 |
| Parenchyma − sinus sO2 | 0–0.10 | Γ₃₇ scale, k_Γ scale | 0.9–1.1, 0.75–1.25 |
| dc/dT scale (all layers) | 0.75–1.25 | Acoustic attenuation scale | 0.7–1.4 |
| Deep echo window depth (mm) | 13–17 | Reference-absorber efficiency | 0.9–1.1 |
| Brain − core gradient (°C) | 0.2–0.8 (+ cooling-dependent) | Scalp below core (°C) | 1–3 |
| NIRS extracerebral weight w, offset b | 0.15–0.35, ±6 % | Probe − scalp thermistor offset (°C) | 0.3–1.0 |

### B. Proposed estimator: joint PA–echo extended Kalman filter

The state is x = [sO2_v, ln f_v, T_b, sO2_s, ln HbT_s, T_s, ln g]ᵀ: venous saturation and effective blood fill of the sinus gate, brain (sinus blood) temperature, scalp saturation, scalp haemoglobin, scalp temperature and coupling gain. The measurement vector of a frame is

z = [ln A_s(λ_k), ln A_b(λ_k) (k = 1…4), Δτ_s, Δτ_b, ln A_ref, T_skin]ᵀ,   (2)

and the measurement model h(x) runs the *nominal* forward model: population head of Table III with the superficial thickness set to the sinus depth measured by the pulse-echo line (the geometry is "ultrasound-guided"), first-order fluence perturbation, nominal Γ(T) and c(T), the same plane-wave acoustics, transducer response and gating as the device (implemented as a precomputed linear map from p₀(z) to the gate envelopes so that one evaluation costs 0.1 ms), differential echo shifts relative to the anchors, ln A_ref = ln g + ln(1 − 0.001(T_probe − 37)) and T_skin = T_probe − 0.65 °C. Each channel's noise variance is the measured noise floor divided by the amplitude (log domain) plus a 2 % model floor; the echo channels use 3 and 4 ns; the reference absorber 1 %; the thermistor channel 0.35 °C. The states follow random walks with per-frame standard deviations of 0.6 % (sO2), 0.4 % (ln f_v, ln HbT_s), 0.012 °C (T_b), 0.02 °C (T_s) and 0.4 % (ln g) for 10-s frames, scaled with the frame length. The filter is the standard EKF [49] with a numerical Jacobian (forward differences, eight model evaluations per frame) and Joseph-form covariance update. Before the update, the normalised innovation of each channel is tested against the 99 % χ²₁ quantile (6.63); channels that fail have their variance inflated by their normalised innovation squared (capped at 100), which is what protects the estimate when a movement changes the coupling or displaces the tissue in a single frame [50]. Temperatures are *anchored* at the first frame: T_b(0) = rectal temperature + 0.4 °C (the population mean brain–rectal gradient) and T_s(0) from the thermistor; both anchors are wrong by up to ±0.5 °C for a given subject, which is why absolute and relative (change from baseline) errors are both reported. The device also reports ±1.96σ intervals from the filter covariance.

The two thermometric channels have complementary nuisance structures. The Grüneisen channel (ln A_b at 800 nm) is corrupted by the coupling gain, by the blood content of the gate and by the fluence, each of which the filter observes elsewhere (reference absorber, spectral consistency across the four wavelengths, scalp gate). The echo channel is immune to all three but is corrupted by tissue displacement and by the unknown value of dc/dT. Neither channel alone identifies the brain temperature in the presence of a movement; together, with the thermistor fixing the scalp, they do.

### C. Baselines and ablations

*Oxygenation:* (B1) the empirical NIRS rScO2 comparator; (B2) linear spectral unmixing of the sinus gate at the four wavelengths without fluence correction, the method of [27, 40] extended to four wavelengths; (B3) fluence-compensated unmixing, i.e. (B2) iterated with the nominal Monte-Carlo fluence model (four fixed-point iterations) but without scalp estimation, temporal filtering or echo channel [17]. *Temperature:* (B4) the rectal probe (true core temperature + 0.1 °C noise); (B5) the scalp thermistor; (B6) classical photoacoustic amplitude thermometry, ΔT = (A/A₀ − 1)/k_Γ at 800 nm in the sinus gate [19, 20]; (B7) echo-shift thermometry from the deep differential shift alone with the nominal dc/dT [24]. *Ablations* of the proposed filter: without the echo channel, without the reference absorber, without fluence correction (fluence frozen at the nominal state), and without depth gating (one gate spanning 0.3–10 mm).

### D. Experiments

**Table V. Experiments.**

| ID | Question | Protocol | Readings |
|---|---|---|---|
| E1 | Optical design | Fluence vs depth, wavelength, bone and beam radius; exposure-limited per-pulse fluence and sinus SNR for 3 sources × 3 transducers × 3 frame lengths; CRLB of sO2 for all wavelength subsets containing 800 nm; perturbation model vs direct Monte Carlo | Φ(z), F₀, p₀, gate amplitudes, noise, SNR, CRLB, errors |
| E2 | Acoustic design | Sinus-gate amplitude, SNR and scalp leakage vs centre frequency (1–7.5 MHz), bone (0–3 mm) and optical pulse width (8–300 ns); echo-shift precision vs SNR and averaging | amplitudes, leakage, SNR, ns and mK precision |
| E3 | Static accuracy | 16 held-out subjects × 4 random states (sO2_v 40–90 %, T_b 32.5–38.5 °C), 12-min stationary recordings, last 20 frames averaged | bias, SD, limits of agreement, R², relative errors |
| E4 | Dynamic clinical scenarios | S1 and S2 on 16 held-out subjects, bedside and wearable devices, all methods and ablations | RMSE, bias, MAE, max error, LoA, event sensitivity, false alarms, latency, 95 % coverage, gradient RMSE, gain RMSE |
| E5 | Sensitivity | S1 (6 h) on 8 subjects per setting: bone 0–3 mm, noise power ×0.25–×16, true/assumed k_Γ 0.7–1.3, true/assumed dc/dT 0.7–1.3, fill factor 0.3–0.7 | RMSE sO2 and T |
| E6 | Safety and power | Pennes model: skin and cortex heating vs average irradiance (0–0.32 W/cm²), electronic heating (0–50 mW/cm²), contact (insulated patch vs open probe), normothermic vs cooled infant; wearable energy budget | ΔT at 5 and 20 min, battery life |

**Statistics.** Subjects with seeds 0–9 were used only for development; all reported results use held-out seeds 10–25 (E3, E4) and 10–17 (E5). Each seed changes anatomy, physiology, noise, movement times and the NIRS comparator. Results are mean ± SD across subjects; the proposed filter is compared with every baseline by the two-sided paired Wilcoxon signed-rank test on the per-subject RMSE. Desaturation alarms are raised when an estimate falls more than 6 % below its 5-min running median; an event counts as detected if an alarm occurs between its onset and 2 min after its end.

## V. Results

All readings are in `results/` of the repository; figures are produced by `experiments/make_figures.py`. Dynamic results are mean ± SD over the 16 held-out subjects.

### A. E1 – Optical design

![](../figures/fig1_optical_design.png)

*Fig. 1. Optical design. (a) On-axis fluence per unit incident fluence versus depth over the open fontanelle for a 5-mm beam radius (layers shaded). (b) Fluence at the sinus surface at 800 nm versus bone thickness and beam radius. (c) Sinus-gate SNR for a 10-s frame at 800 nm for the three source classes and three transducers at the 0.1 W/cm² thermal cap (dashed line: SNR 10). (d) Cramér–Rao bound of the venous saturation for the three best wavelength sets of two, three and four wavelengths.*

**Fluence.** Over the open fontanelle, with a 5-mm beam radius, the fluence at the surface of the sinus (4 mm depth) is 0.44–0.49 times the incident fluence between 690 and 900 nm and 0.39 at 940 nm (Fig. 1(a); Table VI). The low scattering of the neonatal layers makes the first 4 mm almost transparent; inside the blood the fluence falls by an order of magnitude within a millimetre, which is why the sinus signal is a leading-edge signal (Section V-B). One millimetre of bone under the probe costs 4 % of the sinus fluence at 800 nm, 2 mm cost 35 % and 3 mm cost 46 % (Fig. 1(b)); a 3-mm beam radius halves the sinus fluence relative to 5 mm, and 7.5 mm gains another 24 %, so the illumination should fill the fontanelle. The perturbation model reproduces independent Monte Carlo runs at saturations between the table nodes within 1.7 % down to 7 mm and within 4.8 % at 10 mm (Table VI, E1d); the larger deviations at 15–20 mm are dominated by the Monte Carlo variance of the reference runs themselves.

**Table VI. E1 readings at 800 nm over the open fontanelle (beam radius 5 mm) and perturbation-model verification.**

| Quantity | Value |
|---|---|
| Fluence at sinus surface / 10 mm / 20 mm (per incident fluence) | 0.49 / 0.011 / 0.0008 |
| Sinus fluence with 1 / 2 / 3 mm bone | 0.47 / 0.32 / 0.27 |
| Sinus fluence with 3 / 5 / 7.5 mm beam radius | 0.29 / 0.49 / 0.61 |
| Derated single-pulse exposure limit at 690 / 800 / 850 / 900 nm (mJ/cm²) | 9.6 / 15.8 / 20.0 / 25.1 |
| Initial pressure at the sinus edge, 10 mJ/cm² laser / 0.5 mJ/cm² laser diode / 0.05 mJ/cm² LED (Pa) | 2086 / 104 / 10.4 |
| Max. perturbation-model error vs direct Monte Carlo, z ≤ 7 mm / 10 mm / 20 mm | 1.7 % / 4.8 % / 11 % |

**Sources under the exposure and thermal limits.** With all three sources set to the same 0.1 W/cm² average irradiance (Table II), the compact laser at 2.5 Hz per wavelength gives a sinus-gate SNR of 500 per 10-s frame with the single-element probe, the laser-diode stack at 50 Hz gives 100 and the LED array at 500 Hz gives 29 (Fig. 1(c), Table VII), the ratios that (1) predicts. The CMUT patch roughly doubles each figure; the piezo-polymer patch divides it by three. At 2-s frames, needed for the preterm use case, the LED array with the polymer patch falls below SNR 10 (4.5), whereas every laser-diode and laser combination stays above 17. The single-pulse limit is binding only for the compact laser at 690 nm (9.6 mJ/cm² derated), so the 690-nm line of the laser is run at that value.

**Table VII. E1b sinus-gate SNR per frame at 800 nm (0.1 W/cm² average irradiance, open fontanelle, 10 mJ/cm² / 0.5 mJ/cm² / 0.05 mJ/cm² per pulse).**

| Source | Transducer | 2-s frame | 10-s frame | 30-s frame |
|---|---|---|---|---|
| Compact laser | single-element PZT 8 mm | 219 | 497 | 843 |
| Compact laser | flexible PVDF patch | 79 | 162 | 292 |
| Compact laser | CMUT patch | 411 | 961 | 1686 |
| Laser-diode stack | single-element PZT 8 mm | 47 | 103 | 181 |
| Laser-diode stack | flexible PVDF patch | 17 | 35 | 61 |
| Laser-diode stack | CMUT patch | 91 | 189 | 339 |
| LED array | single-element PZT 8 mm | 13 | 29 | 50 |
| LED array | flexible PVDF patch | 4.5 | 11 | 18 |
| LED array | CMUT patch | 26 | 62 | 100 |

**Wavelengths.** The Cramér–Rao bound of the venous saturation (bedside device, 10-s frame, 65 % saturation, 2 % model floor per channel) is 1.9 % for the best pair (690/800 nm) and 3.6 % for the common 750/800-nm pair; three wavelengths bring it to 1.4 % and four to 1.27 % (690/800/850/940 nm). Every one of the ten best sets contains 690 nm, because deoxy-haemoglobin absorbs seven times more than oxy-haemoglobin there, whereas the conventional 750/800/850/900-nm set gives 2.2 %. The set used in all later experiments, 690/800/850/900 nm, is within 7 % of the optimum (1.36 %) and avoids the 940-nm water band, whose absorption is itself temperature dependent; across saturations of 45–85 % and 0–3 mm of bone its bound stays between 0.9 and 2.1 % (Fig. S1). In a separate check on 16 random subjects the same set also gave the lowest structural error of the four candidate sets (1.1 % RMSE against 1.6 % for 750/800/850/900 nm), so the sensitivity of 690 nm to deoxy-haemoglobin outweighs its larger fluence-model sensitivity.


### B. E2 – Acoustic design

![](../figures/fig2_acoustic_design.png)

*Fig. 2. Acoustic design at 800 nm with the compact laser. (a) Sinus-gate SNR per 10-s frame versus transducer centre frequency for 0–3 mm of bone under the probe. (b) Leakage of the scalp signal into the sinus gate and axial resolution versus centre frequency. (c) Sinus-gate amplitude versus centre frequency for 8–300-ns optical pulses. (d) Temperature-equivalent noise of the deep differential echo shift versus the number of pulse-echo lines averaged per frame.*

**Centre frequency.** Because the fluence inside the blood decays within a millimetre, the sinus produces a leading-edge signal whose spectrum extends to several megahertz, and the scalp produces a surface signal of similar bandwidth. Over the open fontanelle the sinus-gate SNR per 10-s frame is highest at 1 MHz (1540), passes through a minimum at 3 MHz (470, where the step-up at the CSF–sinus boundary and the step-down at the membrane–CSF boundary 1 mm above it partly cancel) and recovers at 5–7.5 MHz (1240–1130) (Fig. 2(a)). Bone changes the picture: with 2 mm of bone the SNR at 5 MHz falls eight-fold to 163 while at 1 MHz it falls only three-fold to 555, and with 3 mm of bone only the 1–1.5-MHz elements keep an SNR above 100. The leakage of the scalp signal into the sinus gate is 7–8 % at every centre frequency (Fig. 2(b)), i.e. the gate separation is set by the 4-mm distance between the two sources and the sub-millimetre axial resolution, not by the frequency. The 3-MHz element used in E3–E5 is therefore a conservative choice; a 1–1.5-MHz element would raise the SNR two- to three-fold and tolerate a partly ossified window, which is the design recommendation of Section VI.

**Optical pulse width.** At 1–2 MHz the 80–300-ns pulses of LED and laser-diode sources cost less than 15 % of amplitude relative to an 8-ns laser pulse; at 3 MHz a 300-ns pulse loses 67 %, and at 5 MHz even an 80-ns pulse loses a third (Fig. 2(c)). Long-pulse sources therefore belong with low-frequency elements, which is consistent with the ossification result above.

**Echo-shift thermometry.** The two-way time through the deep segment (CSF, sinus and 9 mm of brain) changes by −16.4 ns/°C and that through the superficial segment by −3.3 ns/°C. With the pad and scalp echoes as references, the differential shift of the deep segment is measured with a standard deviation of 0.29 ns when 100 lines at 30 dB single-line SNR are averaged (18 mK), 0.96 ns at 24 dB (59 mK) and 1.4 ns at 20 dB (88 mK) (Fig. 2(d)); ten lines, as in a 2-s frame, give 84–280 mK. The thermometric precision of the echo channel is therefore not limited by electronic noise but by the non-thermal displacement nuisance (5 ns, i.e. 0.3 °C-equivalent, in the virtual neonate), which is what the fusion with the Grüneisen channel is for.


### C. E3 – Static accuracy over subjects

![](../figures/fig3_static_accuracy.png)

*Fig. 3. Static accuracy over 16 held-out subjects × 4 random states (bedside device, 10-s frames, last 20 frames of a 12-min recording averaged). (a) Estimated versus true venous sO2 for NIRS, linear unmixing, fluence-compensated unmixing and the proposed filter. (b) Bland–Altman plot for sO2. (c), (d) The same for brain temperature with the rectal probe, echo-shift-only and amplitude-only thermometry.*

Over 64 subject–state combinations spanning 40–90 % venous saturation and 32.5–38.5 °C (Table X), the proposed filter recovers the saturation with a bias of −0.1 % and limits of agreement of ±2.9 % (RMSE 1.5 %, R² = 0.986), against −0.6 ± 3.2 % for fluence-compensated unmixing, +1.5 ± 4.3 % for linear unmixing and +6.4 ± 10.3 % for the NIRS comparator (Fig. 3(a), (b)). The residual spread of the photoacoustic methods is structural: it comes from the subject-specific scattering, haematocrit, background absorption and fill factor that the population model does not know, not from noise (the sinus-gate SNR is 65–640 in this cohort). Brain temperature is recovered with a bias of −0.12 °C and limits of ±0.34 °C (RMSE 0.21 °C) by the filter and by echo-shift thermometry alone, since nothing moves in a static recording; the bias is the residual of the rectal anchor. The rectal probe itself is −0.52 ± 0.34 °C from the brain, the scalp thermistor −2.1 ± 1.2 °C, and amplitude-only thermometry, although unbiased on average, has limits of ±1.0 °C because it is exposed to the ±25 % uncertainty of the Grüneisen slope and to the drift of the coupling (Fig. 3(c), (d)). The brain–scalp gradient, a quantity no other bedside method provides, is recovered with an RMSE of 0.32 °C (R² = 0.76).

**Table X. E3 static accuracy over 16 held-out subjects × 4 states (estimate − truth; sO2 in % absolute, temperature in °C).**

| Quantity | Method | Bias | SD | RMSE | LoA | R² |
|---|---|---|---|---|---|---|
| sO2 | NIRS rScO2 (empirical comparator) | +6.4 | 5.2 | 8.3 | −3.9 … +16.7 | 0.83 |
| sO2 | PA linear unmixing | +1.5 | 2.2 | 2.6 | −2.8 … +5.8 | 0.99 |
| sO2 | PA fluence-compensated unmixing | −0.6 | 1.6 | 1.7 | −3.8 … +2.6 | 0.98 |
| sO2 | **Proposed joint EKF** | **−0.1** | **1.5** | **1.5** | **−3.0 … +2.8** | 0.99 |
| T | Rectal probe | −0.52 | 0.18 | 0.55 | −0.86 … −0.18 | 0.99 |
| T | Scalp thermistor | −2.15 | 0.62 | 2.23 | −3.4 … −0.9 | 0.89 |
| T | PA amplitude (800 nm) | −0.12 | 0.50 | 0.51 | −1.1 … +0.9 | 0.95 |
| T | Echo shift only | −0.12 | 0.17 | 0.21 | −0.46 … +0.22 | 0.99 |
| T | **Proposed joint EKF** | **−0.12** | **0.17** | **0.21** | **−0.45 … +0.22** | 0.99 |
| T_brain − T_scalp | Proposed joint EKF | −0.05 | 0.32 | 0.32 | −0.68 … +0.57 | 0.76 |


### D. E4 – Dynamic clinical scenarios

![](../figures/fig4_closed_traces.png)

*Fig. 4. Typical held-out subject (seed 11; sO2 RMSE 0.7 %, temperature RMSE 0.44 °C). (a) S1 therapeutic hypothermia, venous sO2: truth, proposed filter with 95 % band, NIRS and linear unmixing; desaturation events shaded. (b) S1 brain temperature: truth, proposed filter, rectal probe, echo-shift-only and amplitude-only thermometry during cooling, maintenance, rewarming and the seizure-like episode at 6.5 h. (c) Brain–scalp gradient and coupling gain (true and estimated) across movement events. (d) S2 intermittent hypoxaemia at 2-s frames.*

![](../figures/figS2_worst_case_subject.png)

*Fig. S2. Worst-case held-out subject (seed 10: 0.8 mm of bone under the probe, sinus-gate SNR 156): the filter and fluence-compensated unmixing carry a constant positive bias while linear unmixing does not, illustrating the ossification limit quantified in E5.*

![](../figures/fig5_benchmark.png)

*Fig. 5. Benchmark over 16 held-out subjects (median and interquartile range of the per-subject RMSE; Table XI gives mean ± SD). (a) S1 bedside, sO2. (b) S1 bedside, brain temperature. (c) S2 bedside, sO2. (d) S1 wearable (laser-diode stack + CMUT patch), brain temperature.*

Fig. 4 shows a typical held-out subject and Fig. 5 the benchmark; Table XI lists the readings (mean ± SD and median across subjects, Wilcoxon p against the proposed filter). The sinus-gate SNR was 65–640 (mean 340) for the bedside device and 26–155 (mean 96) for the wearable.

**Oxygenation.** In the 10-h hypothermia scenario the proposed filter tracks the venous saturation with a median RMSE of 0.60 % (interquartile range 0.45–0.68 %) with the bedside device and 0.39 % (0.36–0.63 %) with the wearable, against 0.99 % for linear unmixing (p = 0.039), 0.77 % for fluence-compensated unmixing (p = 0.50) and 3.7 % for the NIRS comparator (p = 0.003). One subject, at the 0.8-mm ossification limit of the cohort and with the lowest SNR, carries a constant +12 % bias in the filter (and +8 % in fluence-compensated unmixing) that raises the mean RMSE to 1.4 ± 3.2 % (Fig. S2); the 1-mm tolerance that E5 establishes below is the design consequence. In the 45-min preterm scenario at 2-s frames the filter reaches a median RMSE of 0.97 % (0.91–1.03 %) with a maximum error of 7 % at the nadir of the fastest events, fluence-compensated unmixing 0.93 % (p = 0.98) and NIRS 6.4 % (p < 10⁻⁴). The filter detects 97 % of the hypothermia-scenario desaturations and 92 % of the preterm desaturations with no false alarm, with a median latency of 29 s at 20-s frames and 5.8 s at 2-s frames; the NIRS comparator detects 94–100 % but at 0.26 false alarms per hour in S1 and 79 per hour in S2, because its 2.6 % frame-to-frame precision crosses the 6 % alarm threshold continually at 2-s frames. The 95 % intervals of the filter cover the truth 94 % of the time in S1 and 78 % in S2, where the fastest events outrun the random-walk prior.

**Temperature.** Through cooling, maintenance, rewarming and the seizure-like episode, the filter follows the brain temperature with a median RMSE of 0.38 °C (0.28–0.45 °C; mean 0.42 ± 0.20 °C) in both devices and 0.10 °C (0.04–0.12 °C) in the preterm scenario, against 0.57 °C (p = 0.034) and 0.38 °C (p < 10⁻⁴) for the rectal probe, 2.5 °C and 1.4 °C for the scalp thermistor, and 8.1 °C and 4.5 °C for amplitude-only thermometry, which is destroyed by the coupling losses at every movement (Fig. 4(b)). Relative to the first frame, i.e. without the anchor error, the S1 RMSE is 0.42 °C for the filter and 0.26 °C for the rectal probe: the rectal probe follows the core, and the 0.2–0.8 °C brain–core gradient that grows with cooling is exactly what it misses. The 95 % intervals, which include the anchor uncertainty, cover the truth 83 % (S1) and 100 % (S2) of the time. The filter also returns the brain–scalp gradient with an RMSE of 0.42 °C (S1) and 0.21 °C (S2) and the coupling gain with an RMSE of 0.04 across every movement (Fig. 4(c)).

**Ablations.** Removing the echo channel leaves the brain temperature unobservable: the filter then explains the coupling losses as temperature and diverges (median RMSE 17 °C in S1), and the oxygenation estimate degrades to 1.8 % (S1) and 3.4 % (S2) because the temperature-dependent Grüneisen factor is then mis-attributed to the spectrum. Removing depth gating (one gate over the whole A-line) mixes scalp and sinus blood and triples the oxygenation error (2.0 % and 2.6 %, p < 10⁻³). Removing the reference absorber leaves the oxygenation almost unchanged in S1 (0.64 %) but costs 0.99 % → 1.5 % mean RMSE in S2 (p = 0.018), where the movements are frequent; the coupling gain is then inferred from the spectral consistency alone. Removing the fluence correction changes little in these cohorts (0.70 % in S1, 1.3 % in S2), and in the subject at the ossification limit it is even better, because the fluence model amplifies a wrong superficial geometry; fluence correction pays in the static cohort of E3 (1.5 % against 2.6 % for the uncorrected linear estimate) and in the structural sweep of E5, not in the dynamics.

**Table XI. E4 readings over 16 held-out subjects (RMSE: mean ± SD, median; p: two-sided paired Wilcoxon test against the proposed filter; sens.: fraction of desaturation events detected; FA: false alarms per hour).**

| Scenario | Quantity | Method | RMSE mean ± SD | median | p | sens. | FA/h | latency (s) |
|---|---|---|---|---|---|---|---|---|
| S1 bedside | sO2 (%) | NIRS rScO2 | 5.2 ± 3.5 | 3.70 | 0.003 | 1.00 | 0.26 | 29 |
| S1 bedside | sO2 (%) | PA linear unmixing | 1.10 ± 0.43 | 0.99 | 0.039 | 0.97 | 0 | 25 |
| S1 bedside | sO2 (%) | PA fluence-compensated | 1.20 ± 1.95 | 0.77 | 0.50 | 1.00 | 0.10 | 21 |
| S1 bedside | sO2 (%) | **Proposed EKF** | 1.39 ± 3.22 | **0.60** | – | 0.97 | 0 | 29 |
| S1 bedside | sO2 (%) | EKF − echo | 6.6 ± 8.1 | 1.77 | 0.002 | 0.63 | 1.5 | 51 |
| S1 bedside | sO2 (%) | EKF − reference | 1.45 ± 3.11 | 0.64 | 0.25 | 0.97 | 0 | 29 |
| S1 bedside | sO2 (%) | EKF − fluence corr. | 0.99 ± 0.83 | 0.70 | 0.18 | 0.97 | 0 | 33 |
| S1 bedside | sO2 (%) | EKF − depth gating | 2.8 ± 3.7 | 1.98 | 0.0002 | 0.97 | 0.04 | 42 |
| S1 wearable | sO2 (%) | NIRS rScO2 | 5.2 ± 3.5 | 3.70 | 0.002 | 1.00 | 0.26 | 29 |
| S1 wearable | sO2 (%) | PA linear unmixing | 1.20 ± 0.45 | 1.17 | 0.008 | 0.97 | 0 | 25 |
| S1 wearable | sO2 (%) | PA fluence-compensated | 1.04 ± 1.36 | 0.75 | 0.021 | 1.00 | 0.09 | 21 |
| S1 wearable | sO2 (%) | **Proposed EKF** | 1.09 ± 2.46 | **0.39** | – | 0.97 | 0.04 | 35 |
| S2 bedside | sO2 (%) | NIRS rScO2 | 6.9 ± 1.1 | 6.40 | <10⁻⁴ | 0.94 | 79 | 3.3 |
| S2 bedside | sO2 (%) | PA linear unmixing | 1.41 ± 0.63 | 1.17 | 0.058 | 0.91 | 0 | 4.8 |
| S2 bedside | sO2 (%) | PA fluence-compensated | 1.57 ± 1.50 | 0.93 | 0.98 | 0.92 | 0 | 3.3 |
| S2 bedside | sO2 (%) | **Proposed EKF** | 1.43 ± 1.12 | **0.97** | – | 0.92 | 0 | 5.8 |
| S2 bedside | sO2 (%) | EKF − echo | 4.2 ± 2.7 | 3.36 | <10⁻⁴ | 0.81 | 0 | 12 |
| S2 bedside | sO2 (%) | EKF − reference | 1.55 ± 1.21 | 0.99 | 0.018 | 0.91 | 0 | 5.9 |
| S2 bedside | sO2 (%) | EKF − fluence corr. | 1.54 ± 0.61 | 1.32 | 0.058 | 0.91 | 0 | 6.5 |
| S2 bedside | sO2 (%) | EKF − depth gating | 3.1 ± 1.5 | 2.60 | <10⁻⁴ | 0.89 | 0 | 10 |
| S2 wearable | sO2 (%) | **Proposed EKF** | 1.61 ± 1.10 | 1.13 | – | 0.91 | 0 | 6.4 |
| S1 bedside | T (°C) | Rectal probe | 0.56 ± 0.11 | 0.57 | 0.034 | | | |
| S1 bedside | T (°C) | Scalp thermistor | 2.62 ± 0.62 | 2.53 | <10⁻⁴ | | | |
| S1 bedside | T (°C) | PA amplitude (800 nm) | 7.8 ± 1.2 | 8.07 | <10⁻⁴ | | | |
| S1 bedside | T (°C) | Echo shift only | 0.40 ± 0.22 | 0.37 | 0.001 | | | |
| S1 bedside | T (°C) | **Proposed EKF** | 0.42 ± 0.20 | **0.38** | – | | | |
| S1 bedside | T (°C) | EKF − echo | 121 ± 394 | 16.8 | <10⁻⁴ | | | |
| S1 wearable | T (°C) | **Proposed EKF** | 0.42 ± 0.20 | **0.39** | – | | | |
| S2 bedside | T (°C) | Rectal probe | 0.40 ± 0.10 | 0.38 | <10⁻⁴ | | | |
| S2 bedside | T (°C) | Scalp thermistor | 1.34 ± 0.32 | 1.40 | <10⁻⁴ | | | |
| S2 bedside | T (°C) | PA amplitude (800 nm) | 4.5 ± 1.7 | 4.46 | <10⁻⁴ | | | |
| S2 bedside | T (°C) | Echo shift only | 0.092 ± 0.047 | 0.10 | 0.001 | | | |
| S2 bedside | T (°C) | **Proposed EKF** | 0.089 ± 0.049 | **0.10** | – | | | |
| S2 wearable | T (°C) | **Proposed EKF** | 0.089 ± 0.050 | 0.09 | – | | | |


### E. E5 – Sensitivity

![](../figures/fig6_sensitivity.png)

*Fig. 6. Sensitivity of the sO2 (top) and brain-temperature (bottom) RMSE in the 6-h hypothermia scenario (8 subjects per setting) to bone under the probe, noise power, the true/assumed Grüneisen slope, the true/assumed speed-of-sound coefficient and the sinus fill factor.*

Fig. 6 and Table XII give the RMSE of the 6-h hypothermia scenario on 8 subjects per setting. **Ossification** is the one structural parameter that matters for oxygenation: the filter's RMSE is 0.7–1.5 % with 0–1 mm of bone under the probe, 4.6 % at 1.5 mm and 6.5–7.1 % at 2–3 mm, where fluence-compensated unmixing reaches 9.7 % and 23 %; the temperature estimate is unaffected (0.37–0.39 °C) because the echo channel does not depend on the optical model. The device is therefore specified for an open anterior fontanelle with at most 1 mm of bone under the aperture, which the pulse-echo line can verify at set-up; a 1–1.5-MHz element (Section V-B) would extend this margin acoustically but not optically. **Noise** power from ×0.25 to ×16 (SNR 4 to 0.25 of nominal) changes the oxygenation RMSE from 0.77 % to 0.83 % and the temperature RMSE not at all, so the wearable's lower SNR and a halved thermal budget are both inside the margin. **Grüneisen-slope** errors of ±30 % leave both estimates unchanged (0.75–0.77 %, 0.37 °C), because temperature is anchored by the echo channel and the slope error is represented in the measurement covariance. **Speed-of-sound** errors of ±30 % are the dominant temperature uncertainty: the RMSE rises to 0.82 °C (−30 %) and 0.88 °C (+30 %), against 0.79 and 0.95 °C for echo-shift thermometry alone; this coefficient must be calibrated, which the Grüneisen channel can help with over long cooling ramps. The **fill factor** of the sinus between 0.3 and 0.7 changes nothing (0.76–0.82 %), confirming that the blood content of the gate is correctly absorbed by the nuisance state.

**Table XII. E5 sensitivity (RMSE, 8 subjects per setting, S1 for 6 h, bedside device).**

| Setting | Value | sO2: proposed | sO2: fluence-comp. | sO2: NIRS | T: proposed | T: echo only | T: rectal |
|---|---|---|---|---|---|---|---|
| bone (mm) | 0 / 0.5 / 1 / 1.5 / 2 / 3 | 1.5 / 0.7 / 1.4 / 4.6 / 7.1 / 6.5 | 2.3 / 1.2 / 2.4 / 4.5 / 9.7 / 23 | 8.6 | 0.39 / 0.38 / 0.38 / 0.39 / 0.37 / 0.37 | 0.35 / 0.33 / 0.34 / 0.34 / 0.35 / 0.37 | 0.77 |
| noise power × | 0.25 / 4 / 16 | 0.77 / 0.76 / 0.83 | 1.23 / 1.26 / 1.34 | 8.6 | 0.37 / 0.37 / 0.38 | 0.33 | 0.77 |
| true/assumed k_Γ | 0.7 / 1.3 | 0.75 / 0.77 | 1.24 / 1.23 | 8.6 | 0.37 / 0.37 | 0.33 | 0.77 |
| true/assumed dc/dT | 0.7 / 1.3 | 0.72 / 0.82 | 1.23 / 1.24 | 8.6 | 0.82 / 0.88 | 0.79 / 0.95 | 0.77 |
| sinus fill factor | 0.3 / 0.7 | 0.82 / 0.76 | 1.72 / 0.95 | 8.6 | 0.37 / 0.37 | 0.33 | 0.77 |


### F. E6 – Thermal safety and power budget

![](../figures/fig7_thermal_safety.png)

*Fig. 7. Pennes bioheat model of the tissue under the probe. (a) Scalp temperature rise after 20 min versus average NIR irradiance for an insulating patch and an open probe, with and without 50 mW/cm² of electronic self-heating. (b) Cortical temperature rise for the cooled infant.*

**Optical heating.** In the Pennes model the scalp under an insulating patch warms by 0.37 °C per 20 mW/cm² of average near-infrared irradiance after 20 min (0.33 °C under an open probe), i.e. 0.93 °C at 50 mW/cm², 1.86 °C at the 0.1 W/cm² assumed in Table II and 6.0 °C at the undated ANSI average-power limit of 0.32 W/cm² (Fig. 7(a), Table VIII); 90 % of the rise is reached within 5 min. The cortex of a cooled infant warms by 0.29 °C at 50 mW/cm² and 0.57 °C at 0.1 W/cm² (Fig. 7(b)), which is not negligible against a 33.5 °C target, and the absolute skin temperature stays below the 41 °C applied-part limit of IEC 60601-1 in every case (35.3 °C at 0.1 W/cm² for the cooled infant). A 1 °C scalp limit therefore corresponds to a continuous average irradiance of about 50 mW/cm², or to the 0.1 W/cm² of Table II at a duty cycle of 50 % or less. Since the SNR under an average-power cap scales with the square root of the cap (1), halving it divides the SNRs of Table VII by 1.4; the ×4 noise-power setting of E5 covers this case with margin.

**Electronic heating.** Heat from the driver and front-end that reaches the skin is the larger hazard: 20 mW/cm² conducted into the scalp raises it by 2.4 °C and 50 mW/cm² by 6 °C, independently of the optical load (Table VIII), because the insulated contact can shed heat only by conduction into the tissue. The patch must therefore conduct its dissipation to the air side, and the heat flux into the skin must be kept below about 5 mW/cm² (0.6 °C), which the thermistor at the pad–skin interface can verify continuously.

**Table VIII. E6 scalp temperature rise after 20 min (Pennes model, 37 °C infant; cooled infant within 0.1 °C of these values).**

| Average irradiance (W/cm²) | Insulated patch | Insulated patch + 20 mW/cm² electronics | Open probe | Cortex rise, cooled infant |
|---|---|---|---|---|
| 0.02 | 0.37 | 2.79 | 0.33 | 0.11 |
| 0.05 | 0.93 | 3.35 | 0.83 | 0.29 |
| 0.10 | 1.86 | 4.28 | 1.66 | 0.57 |
| 0.20 | 3.73 | 6.15 | 3.32 | 1.14 |
| 0.32 | 5.97 | 8.39 | 5.32 | 1.83 |

**Power budget.** With a 30 % wall-plug efficiency the laser-diode stack draws 0.26 W for four wavelengths at 50 Hz each and the full patch (front end, ADC, controller and radio at 0.25 W) 0.51 W, or 0.32 W when the source runs 25 % of the time: 14 h and 23 h on a 7.4-Wh battery (Table IX). The LED array is less efficient at the same average irradiance (0.77 W, 9.6 h) because of its lower wall-plug efficiency, and the compact laser at 2 % efficiency (4.2 W) is a mains-powered bedside device. The duty-cycled laser-diode patch is thus the wearable configuration carried into E4: 25 % duty reduces the average irradiance to 25 mW/cm² (0.46 °C scalp rise) and still delivers the 10-s-frame SNR of Table VII whenever the source is on.

**Table IX. E6 wearable power budget (four wavelengths, 5-mm beam radius, 0.1 W/cm² while the source is on, 0.25 W for electronics).**

| Source | Wall-plug eff. | Optical energy per pulse (mJ) | Source power (W) | Total, continuous (W) | Battery life, continuous (h) | Total, 25 % duty (W) | Battery life, 25 % duty (h) |
|---|---|---|---|---|---|---|---|
| LED array | 0.15 | 0.039 | 0.52 | 0.77 | 9.6 | 0.38 | 19 |
| Laser-diode stack | 0.30 | 0.39 | 0.26 | 0.51 | 14 | 0.32 | 23 |
| Compact laser | 0.02 | 7.9 | 3.9 | 4.2 | 1.8 (mains) | 1.2 | 6.0 |


## VI. Discussion

### A. Design recommendations

The exploration yields six design rules. (1) *Target the sagittal sinus through the fontanelle.* The neonatal superficial layers are nearly transparent and the sinus is the strongest, best-defined absorber under the window; its blood is venous, which is the clinically relevant compartment, and its leading edge is a broadband acoustic source whose position the pulse-echo line gives for free. (2) *Spend the exposure budget on energy per pulse, not on repetition rate* (1): under the average-power cap that the thermal model imposes, a 2.5-Hz, 10-mJ/cm² source beats a 500-Hz LED array fourteen-fold in SNR at the same scalp heating. The laser-diode stack at 50 Hz and 0.5 mJ/cm² is the middle ground that makes a battery-powered patch possible with an SNR of 100–190 per 10-s frame. (3) *Use 690 nm.* It carries most of the deoxy-haemoglobin contrast and halves the Cramér–Rao bound relative to 750-nm-based sets; with 800 nm (isosbestic, thermometry) and two longer lines the bound is 1.4 %. (4) *Go low in acoustic frequency.* A 1–1.5-MHz element gives two to three times the SNR of the 3-MHz element used here, tolerates the 100–300-ns pulses of LED and laser-diode sources and keeps working over a partly ossified window; the 4-mm scalp–sinus distance provides the depth separation, not the bandwidth. (5) *Budget heat, not only light.* Fifty milliwatts per square centimetre of continuous near-infrared irradiance, or 0.1 W/cm² at 50 % duty, keeps the scalp within 1 °C; electronic heat conducted into the skin must stay below 5 mW/cm², and the pad thermistor should supervise both. (6) *Verify the window.* The pulse-echo line should confirm at set-up that the sinus surface lies within 5 mm and that no bone echo precedes it, because 1.5 mm of bone triples the oxygenation error and 2 mm makes it unusable.

### B. What the joint estimator adds

Two of the three outputs of the device exist only because of the joint estimation. Brain temperature is unobservable from the photoacoustic amplitude alone once the coupling changes (the filter without the echo channel diverges, and classical amplitude thermometry errs by 4–8 °C in the scenarios), and the echo channel alone cannot tell a cooled scalp from a cooled brain; with the thermistor fixing the scalp and the differential echo shifts fixing both segments, the filter returns the brain temperature within 0.4 °C over a 10-h cooling–rewarming course and the brain–scalp gradient within 0.4 °C. For oxygenation the gain over the best per-frame method is modest in the median (0.60 % against 0.77 % and 0.99 %) but systematic in the interquartile range (0.45–0.68 % against 0.40–1.02 % and 0.81–1.24 %), and the filter adds what a monitor needs: a coupling-quality index that explains every movement artefact (gain RMSE 0.04), 95 % intervals that cover the truth 78–94 % of the time, and alarms with no false positive. The ablations locate the value: depth gating and the echo channel are essential, the reference absorber matters when movements are frequent, and the fluence correction matters when the saturation range is wide (E3) but can amplify a wrong geometry, which argues for verifying the window (rule 6) rather than for dropping the correction. The weakest link is the speed-of-sound coefficient, whose ±30 % uncertainty doubles the temperature error; it is a calibration task for the phantom and animal studies, and the long, slow cooling ramps of therapeutic hypothermia are themselves a calibration opportunity, since the Grüneisen channel sees the same temperature change with an independent coefficient.

### C. Relation to published measurements

The simulated venous saturations and their accuracy can be compared with the piglet validation of transfontanelle sagittal-sinus photoacoustics, which reported root-mean-square errors below 10 % against blood-gas co-oximetry with two wavelengths and no fluence model [27, 28], and with the 60–80 % sinus saturations measured optoacoustically in human newborns [26]. The temperature resolution is in line with the 0.15 °C sensitivity of photoacoustic thermometry at 2-s averaging [20] and the 0.6 °C absolute accuracy of combined Grüneisen/speed-of-sound thermometry at 9 mm depth [25]; the present filter achieves its accuracy relative to an anchor, which is the clinically available rectal probe, and its contribution is the continuous tracking of the brain–core and brain–scalp differences that MR thermometry shows to be clinically relevant [5, 6]. The NIRS comparator reproduces the inter-device offsets and precision of the literature [8, 9] by construction, so the comparison in Fig. 3 and Fig. 5 is a comparison with the published behaviour of cerebral oximeters, not with a simulated optical instrument.

### D. Limitations

The study is in-silico. Its limitations are those of its models. (i) Light transport is layered and the sinus is a slab; the real sinus is a 3–5-mm channel with curved walls, so the fill factor and the edge signal will differ, which is why the fill factor is a nuisance state rather than a known constant. (ii) Acoustic propagation is one-dimensional plane-wave, which ignores diffraction, the finite element size, refraction at the bone edge of the fontanelle and the directivity of a patch element; these mainly change the absolute gate amplitudes, which the gain and fill states absorb, but they can also colour the spectrum if the beam and the acoustic aperture are misaligned. (iii) Thermal strain, pulsatile brain motion and probe pressure were represented by an Ornstein–Uhlenbeck nuisance on the echo channel; real echo-shift thermometry in a moving infant will be harder, which the robustness analysis addresses only in part. (iv) The Grüneisen and speed-of-sound temperature coefficients were taken from adult tissue and blood measurements and randomised by ±25 %; neonatal values are unknown and will have to be calibrated. (v) The chromophore model omits melanin, hair and bilirubin, which will attenuate and colour the fluence in some infants. (vi) Skin exposure limits for neonates are not standardised; the derated ANSI limits and the thermal budget are proposals. (vii) The NIRS comparator is empirical. (viii) The scalp gate includes the pad–skin signal and its interpretation as scalp blood is approximate.

### E. Validation plan

The results define the targets for hardware validation: (1) phantom tests with a blood-filled 4-mm channel at 4–7 mm depth under a layered scalp/membrane phantom at 33–39 °C, with controlled saturation (tonometry) and temperature, to calibrate k_Γ and dc/dT and to verify the ±2 % and ±0.2 °C static targets; (2) coupling and motion tests on the phantom to verify the reference-absorber gain correction and the differential echo-shift immunity; (3) a neonatal piglet study with graded hypoxia and whole-body cooling against sagittal-sinus blood gases and an implanted brain thermistor, following [27]; (4) a first-in-human observational study in cooled infants against rectal temperature and arterial/venous blood gases, with MR thermometry where available [5], under IEC 60601 applied-part temperature limits [63] and the photobiological limits of [53, 64].

## VII. Conclusion

A photon-to-phonon monitor that couples four near-infrared lines and a low-frequency ultrasound element to the anterior fontanelle can read the oxygen saturation of cerebral venous blood and the temperature of the brain at the same time, continuously, within the optical and thermal exposure limits of a neonate. The design study sets the source class, the repetition rate, the wavelengths, the centre frequency and the heat budget from first principles and from the anatomy of the infant, and the joint extended Kalman filter turns depth-gated photoacoustic spectra, Grüneisen and speed-of-sound thermometry, a reference absorber and a thermistor into venous saturation within ±3 %, brain temperature within ±0.4 °C and the brain–scalp gradient, with calibrated intervals and artefact-free alarms, on virtual neonates whose anatomy, physiology and acoustics the filter does not know. A bedside version with a compact laser and a battery-powered laser-diode patch both meet the targets; LED excitation does at 10-s frames but not at the 2-s frames the preterm use case needs. Everything reported here is simulated; the numbers are the specification for the phantom, animal and clinical studies that must follow, and the code, readings and figures are released so that those studies can start from the same model.

## Appendix: Reproducibility

The repository contains the Monte Carlo code, the fluence tables, the virtual neonate, the estimators, every experiment script, all readings (CSV/NPZ) and the figure scripts. `python experiments/build_fluence_table.py` (about 10 min on four cores), `python experiments/run_design.py`, `python experiments/run_dynamic.py` (about two hours on four cores) and `python experiments/make_figures.py` reproduce every number and figure in this paper from a fresh clone; `--quick` runs a smoke test in minutes.

## Acknowledgment

The author thanks the open-source communities behind NumPy, SciPy, Numba and Matplotlib.

## References

[1] S. Shankaran, A. R. Laptook, R. A. Ehrenkranz, et al., "Whole-body hypothermia for neonates with hypoxic-ischemic encephalopathy," *N. Engl. J. Med.*, vol. 353, no. 15, pp. 1574–1584, 2005, doi: 10.1056/NEJMcps050929.

[2] D. V. Azzopardi, B. Strohm, A. D. Edwards, et al., "Moderate hypothermia to treat perinatal asphyxial encephalopathy," *N. Engl. J. Med.*, vol. 361, no. 14, pp. 1349–1358, 2009, doi: 10.1056/NEJMoa0900854.

[3] S. E. Jacobs, M. Berg, R. Hunt, W. O. Tarnow-Mordi, T. E. Inder, and P. G. Davis, "Cooling for newborns with hypoxic ischaemic encephalopathy," *Cochrane Database Syst. Rev.*, no. 1, Art. no. CD003311, 2013, doi: 10.1002/14651858.CD003311.pub3.

[4] S. Shankaran, A. R. Laptook, A. Pappas, et al., "Effect of depth and duration of cooling on deaths in the NICU among neonates with hypoxic ischemic encephalopathy: A randomized clinical trial," *JAMA*, vol. 312, no. 24, pp. 2629–2639, 2014, doi: 10.1001/jama.2014.16058.

[5] T.-W. Wu, C. McLean, P. Friedlich, et al., "Brain temperature in neonates with hypoxic-ischemic encephalopathy during therapeutic hypothermia," *J. Pediatr.*, vol. 165, no. 6, pp. 1129–1134, 2014, doi: 10.1016/j.jpeds.2014.07.022.

[6] Z. P. Owji, G. Gilbert, C. Saint-Martin, and P. Wintermark, "Brain temperature is increased during the first days of life in asphyxiated newborns: Developing brain injury despite hypothermia treatment," *AJNR Am. J. Neuroradiol.*, vol. 38, no. 11, pp. 2180–2186, 2017, doi: 10.3174/ajnr.A5350.

[7] A. A. Garvey and E. M. Dempsey, "Applications of near infrared spectroscopy in the neonate," *Curr. Opin. Pediatr.*, vol. 30, no. 2, pp. 209–215, 2018, doi: 10.1097/MOP.0000000000000599 (DOI to be verified).

[8] L. M. L. Dix, F. van Bel, W. Baerts, and P. M. A. Lemmers, "Comparing near-infrared spectroscopy devices and their sensors for monitoring regional cerebral oxygen saturation in the neonate," *Pediatr. Res.*, vol. 74, no. 5, pp. 557–563, 2013, doi: 10.1038/pr.2013.133.

[9] S. Kleiser, D. Ostojic, N. Nasseri, et al., "In vivo precision assessment of a near-infrared spectroscopy-based tissue oximeter (OxyPrem v1.3) in neonates considering systemic hemodynamic fluctuations," *J. Biomed. Opt.*, vol. 23, no. 6, Art. no. 067003, 2018, doi: 10.1117/1.JBO.23.6.067003.

[10] S. Hyttel-Sorensen, A. Pellicer, T. Alderliesten, et al., "Cerebral near infrared spectroscopy oximetry in extremely preterm infants: phase II randomised clinical trial," *BMJ*, vol. 350, Art. no. g7635, 2015, doi: 10.1136/bmj.g7635.

[11] M. L. Hansen, A. Pellicer, S. Hyttel-Sørensen, et al., "Cerebral oximetry monitoring in extremely preterm infants," *N. Engl. J. Med.*, vol. 388, no. 16, pp. 1501–1511, 2023, doi: 10.1056/NEJMoa2207554.

[12] J. M. Di Fiore, P. M. MacFarlane, and R. J. Martin, "Intermittent hypoxemia in preterm infants," *Clin. Perinatol.*, vol. 46, no. 3, pp. 553–565, 2019, doi: 10.1016/j.clp.2019.05.006.

[13] C. J. Rhee, C. S. da Costa, T. Austin, K. M. Brady, M. Czosnyka, and J. K. Lee, "Neonatal cerebrovascular autoregulation," *Pediatr. Res.*, vol. 84, no. 5, pp. 602–610, 2018, doi: 10.1038/s41390-018-0141-6.

[14] M. Xu and L. V. Wang, "Photoacoustic imaging in biomedicine," *Rev. Sci. Instrum.*, vol. 77, no. 4, Art. no. 041101, 2006, doi: 10.1063/1.2195024.

[15] P. Beard, "Biomedical photoacoustic imaging," *Interface Focus*, vol. 1, no. 4, pp. 602–631, 2011, doi: 10.1098/rsfs.2011.0028.

[16] L. V. Wang and S. Hu, "Photoacoustic tomography: In vivo imaging from organelles to organs," *Science*, vol. 335, no. 6075, pp. 1458–1462, 2012, doi: 10.1126/science.1216210.

[17] B. Cox, J. G. Laufer, S. R. Arridge, and P. C. Beard, "Quantitative spectroscopic photoacoustic imaging: a review," *J. Biomed. Opt.*, vol. 17, no. 6, Art. no. 061202, 2012, doi: 10.1117/1.JBO.17.6.061202.

[18] I. V. Larina, K. V. Larin, and R. O. Esenaliev, "Real-time optoacoustic monitoring of temperature in tissues," *J. Phys. D: Appl. Phys.*, vol. 38, no. 15, pp. 2633–2639, 2005, doi: 10.1088/0022-3727/38/15/015 (DOI to be verified).

[19] J. Shah, S. Park, S. Aglyamov, et al., "Photoacoustic imaging and temperature measurement for photothermal cancer therapy," *J. Biomed. Opt.*, vol. 13, no. 3, Art. no. 034024, 2008, doi: 10.1117/1.2940362.

[20] M. Pramanik and L. V. Wang, "Thermoacoustic and photoacoustic sensing of temperature," *J. Biomed. Opt.*, vol. 14, no. 5, Art. no. 054024, 2009, doi: 10.1117/1.3247155.

[21] E. Petrova, S. Ermilov, R. Su, V. Nadvoretskiy, A. Conjusteau, and A. Oraevsky, "Using optoacoustic imaging for measuring the temperature dependence of Grüneisen parameter in optically absorbing solutions," *Opt. Express*, vol. 21, no. 21, pp. 25077–25090, 2013, doi: 10.1364/OE.21.025077.

[22] E. V. Petrova, A. A. Oraevsky, and S. A. Ermilov, "Red blood cell as a universal optoacoustic sensor for non-invasive temperature monitoring," *Appl. Phys. Lett.*, vol. 105, no. 9, Art. no. 094103, 2014, doi: 10.1063/1.4894635.

[23] J. C. Bamber and C. R. Hill, "Ultrasonic attenuation and propagation speed in mammalian tissues as a function of temperature," *Ultrasound Med. Biol.*, vol. 5, no. 2, pp. 149–157, 1979, doi: 10.1016/0301-5629(79)90083-8 (DOI to be verified).

[24] R. Seip and E. S. Ebbini, "Noninvasive estimation of tissue temperature response to heating fields using diagnostic ultrasound," *IEEE Trans. Biomed. Eng.*, vol. 42, no. 8, pp. 828–839, 1995, doi: 10.1109/10.398644.

[25] J. Yao, H. Ke, S. Tai, Y. Zhou, and L. V. Wang, "Absolute photoacoustic thermometry in deep tissue," *Opt. Lett.*, vol. 38, no. 24, pp. 5228–5231, 2013, doi: 10.1364/OL.38.005228.

[26] I. Y. Petrov, K. E. Wynne, Y. Petrov, et al., "Noninvasive, optoacoustic monitoring of cerebral venous blood oxygenation in newborns," *Proc. SPIE*, vol. 8223, Art. no. 82231M, 2012, doi: 10.1117/12.914657.

[27] J. Kang, E. M. Boctor, S. Adams, et al., "Validation of noninvasive photoacoustic measurements of sagittal sinus oxyhemoglobin saturation in hypoxic neonatal piglets," *J. Appl. Physiol.*, vol. 125, no. 4, pp. 983–989, 2018, doi: 10.1152/japplphysiol.00184.2018.

[28] J. Kang, R. C. Koehler, S. Adams, E. M. Graham, and E. M. Boctor, "Light-emitting diode-based transcranial photoacoustic measurement of sagittal sinus oxyhemoglobin saturation in hypoxic neonatal piglets," bioRxiv, 2020 (preprint), doi: 10.1101/2020.08.22.262451.

[29] R. Manwar, L. S. McGuire, M. T. Islam, et al., "Transfontanelle photoacoustic imaging for in-vivo cerebral oxygenation measurement," *Sci. Rep.*, vol. 12, 2022, doi: 10.1038/s41598-022-19350-x.

[30] R. Manwar, K. Kratkiewicz, S. Mahmoodkalayeh, et al., "Development and characterization of transfontanelle photoacoustic imaging system for detection of intracranial hemorrhages and measurement of brain oxygenation: Ex-vivo," *Photoacoustics*, vol. 32, Art. no. 100538, 2023, doi: 10.1016/j.pacs.2023.100538.

[31] J. Benavides-Lara, R. Manwar, L. S. McGuire, et al., "Transfontanelle photoacoustic imaging of intraventricular brain hemorrhages in live sheep," *Photoacoustics*, vol. 33, Art. no. 100549, 2023, doi: 10.1016/j.pacs.2023.100549.

[32] C. Wang, X. Li, H. Hu, et al., "Monitoring of the central blood pressure waveform via a conformal ultrasonic device," *Nat. Biomed. Eng.*, vol. 2, no. 9, pp. 687–695, 2018, doi: 10.1038/s41551-018-0287-x.

[33] C. Wang, B. Qi, M. Lin, et al., "Continuous monitoring of deep-tissue haemodynamics with stretchable ultrasonic phased arrays," *Nat. Biomed. Eng.*, vol. 5, no. 7, pp. 749–758, 2021, doi: 10.1038/s41551-021-00763-4.

[34] X. Gao, X. Chen, H. Hu, et al., "A photoacoustic patch for three-dimensional imaging of hemoglobin and core temperature," *Nat. Commun.*, vol. 13, Art. no. 7757, 2022, doi: 10.1038/s41467-022-35455-3.

[35] H. Hu, H. Huang, M. Li, et al., "A wearable cardiac ultrasound imager," *Nature*, vol. 613, no. 7945, pp. 667–675, 2023, doi: 10.1038/s41586-022-05498-z.

[36] M. Lin, Z. Zhang, X. Gao, et al., "A fully integrated wearable ultrasound system to monitor deep tissues in moving subjects," *Nat. Biotechnol.*, 2023, doi: 10.1038/s41587-023-01800-0.

[37] R. Hochuli, L. An, P. C. Beard, and B. T. Cox, "Estimating blood oxygenation from photoacoustic images: can a simple linear spectroscopic inversion ever work?," *J. Biomed. Opt.*, vol. 24, no. 12, Art. no. 121914, 2019, doi: 10.1117/1.JBO.24.12.121914.

[38] L. Atallah, E. Bongers, B. Lamichhane, and S. Bambang-Oetomo, "Unobtrusive monitoring of neonatal brain temperature using a zero-heat-flux sensor matrix," *IEEE J. Biomed. Health Inform.*, vol. 20, no. 1, pp. 100–107, 2016, doi: 10.1109/JBHI.2014.2385103 (DOI to be verified).

[39] A. J. Lyon and Y. Freer, "Goals and options in keeping preterm babies warm," *Arch. Dis. Child. Fetal Neonatal Ed.*, vol. 96, no. 1, pp. F71–F74, 2011, doi: 10.1136/adc.2009.161158.

[40] I. Y. Petrov, Y. Petrov, D. S. Prough, et al., "Optoacoustic monitoring of cerebral venous blood oxygenation though intact scalp in large animals," *Opt. Express*, vol. 20, no. 4, pp. 4159–4167, 2012, doi: 10.1364/OE.20.004159.

[41] S. Tzoumas, A. Nunes, I. Olefir, et al., "Eigenspectra optoacoustic tomography achieves quantitative blood oxygenation imaging deep in tissues," *Nat. Commun.*, vol. 7, Art. no. 12121, 2016, doi: 10.1038/ncomms12121.

[42] T. Kirchner, J. Gröhl, and L. Maier-Hein, "Context encoding enables machine learning-based quantitative photoacoustics," *J. Biomed. Opt.*, vol. 23, no. 5, Art. no. 056008, 2018, doi: 10.1117/1.JBO.23.5.056008.

[43] A. Hariri, J. Lemaster, J. Wang, et al., "The characterization of an economic and portable LED-based photoacoustic imaging system to facilitate molecular imaging," *Photoacoustics*, vol. 9, pp. 10–20, 2018, doi: 10.1016/j.pacs.2017.11.001.

[44] Y. Zhu, G. Xu, J. Yuan, et al., "Light emitting diodes based photoacoustic imaging and potential clinical applications," *Sci. Rep.*, vol. 8, Art. no. 9885, 2018, doi: 10.1038/s41598-018-28131-4.

[45] Y. Zhu, T. Feng, Q. Cheng, et al., "Towards clinical translation of LED-based photoacoustic imaging: A review," *Sensors*, vol. 20, no. 9, Art. no. 2484, 2020, doi: 10.3390/s20092484.

[46] W. Xia, M. Kuniyil Ajith Singh, E. Maneas, et al., "Handheld real-time LED-based photoacoustic and ultrasound imaging system for accurate visualization of clinical metal needles and superficial vasculature to guide minimally invasive procedures," *Sensors*, vol. 18, no. 5, Art. no. 1394, 2018, doi: 10.3390/s18051394.

[47] P. K. Upputuri and M. Pramanik, "Fast photoacoustic imaging systems using pulsed laser diodes: a review," *Biomed. Eng. Lett.*, vol. 8, no. 2, pp. 167–181, 2018, doi: 10.1007/s13534-018-0060-9.

[48] M. Erfanzadeh and Q. Zhu, "Photoacoustic imaging with low-cost sources; A review," *Photoacoustics*, vol. 14, pp. 1–11, 2019, doi: 10.1016/j.pacs.2019.01.004.

[49] R. E. Kalman, "A new approach to linear filtering and prediction problems," *J. Basic Eng.*, vol. 82, no. 1, pp. 35–45, 1960, doi: 10.1115/1.3662552.

[50] Q. Li, R. G. Mark, and G. D. Clifford, "Robust heart rate estimation from multiple asynchronous noisy sources using signal quality indices and a Kalman filter," *Physiol. Meas.*, vol. 29, no. 1, pp. 15–32, 2008, doi: 10.1088/0967-3334/29/1/002.

[51] M. J. Buller, W. J. Tharion, S. N. Cheuvront, et al., "Estimation of human core temperature from sequential heart rate observations," *Physiol. Meas.*, vol. 34, no. 7, pp. 781–798, 2013, doi: 10.1088/0967-3334/34/7/781 (DOI to be verified).

[52] J. Dudink, S. J. Steggerda, S. Horsch, et al., "State-of-the-art neonatal cerebral ultrasound: technique and reporting," *Pediatr. Res.*, vol. 87, Suppl. 1, pp. 3–12, 2020, doi: 10.1038/s41390-020-0776-y.

[53] ANSI Z136.1-2022, *American National Standard for Safe Use of Lasers*. Orlando, FL, USA: Laser Institute of America, 2022.

[54] Y. Fukui, Y. Ajichi, and E. Okada, "Monte Carlo prediction of near-infrared light propagation in realistic adult and neonatal head models," *Appl. Opt.*, vol. 42, no. 16, pp. 2881–2887, 2003, doi: 10.1364/AO.42.002881.

[55] M. Dehaes, P. E. Grant, D. D. Sliva, et al., "Assessment of the frequency-domain multi-distance method to evaluate the brain optical properties: Monte Carlo simulations from neonate to adult," *Biomed. Opt. Express*, vol. 2, no. 3, pp. 552–567, 2011, doi: 10.1364/BOE.2.000552.

[56] S. L. Jacques, "Optical properties of biological tissues: a review," *Phys. Med. Biol.*, vol. 58, no. 11, pp. R37–R61, 2013, doi: 10.1088/0031-9155/58/11/R37.

[57] S. J. Matcher, C. E. Elwell, C. E. Cooper, M. Cope, and D. T. Delpy, "Performance comparison of several published tissue near-infrared spectroscopy algorithms," *Anal. Biochem.*, vol. 227, no. 1, pp. 54–68, 1995, doi: 10.1006/abio.1995.1252.

[58] N. Bosschaart, G. J. Edelman, M. C. G. Aalders, T. G. van Leeuwen, and D. J. Faber, "A literature review and novel theoretical approach on the optical properties of whole blood," *Lasers Med. Sci.*, vol. 29, no. 2, pp. 453–479, 2014, doi: 10.1007/s10103-013-1446-7.

[59] G. M. Hale and M. R. Querry, "Optical constants of water in the 200-nm to 200-µm wavelength region," *Appl. Opt.*, vol. 12, no. 3, pp. 555–563, 1973, doi: 10.1364/AO.12.000555 (DOI to be verified).

[60] L. Wang, S. L. Jacques, and L. Zheng, "MCML—Monte Carlo modeling of light transport in multi-layered tissues," *Comput. Methods Programs Biomed.*, vol. 47, no. 2, pp. 131–146, 1995, doi: 10.1016/0169-2607(95)01640-F.

[61] F. J. Fry and J. E. Barger, "Acoustical properties of the human skull," *J. Acoust. Soc. Am.*, vol. 63, no. 5, pp. 1576–1590, 1978, doi: 10.1121/1.381852.

[62] L. Mohammadi, H. Behnam, J. Tavakkoli, and M. R. N. Avanaki, "Skull's photoacoustic attenuation and dispersion modeling with deterministic ray-tracing: Towards real-time aberration correction," *Sensors*, vol. 19, no. 2, Art. no. 345, 2019, doi: 10.3390/s19020345.

[63] IEC 60601-1, *Medical electrical equipment – Part 1: General requirements for basic safety and essential performance* (applied-part surface temperature limits), and IEC 60601-2-19 (infant incubators). Geneva, Switzerland: IEC.

[64] IEC 62471:2006, *Photobiological safety of lamps and lamp systems*. Geneva, Switzerland: IEC, 2006.
