# CFET generic design rules (conceptual 3-nm-class rule set)

These rules are a self-consistent *generic* rule set used only to produce
DRC-clean conceptual layouts for the UCM-CFET paper. They are not a foundry PDK
and make no tape-out claim. All dimensions in nm. GDSII is 2-D, so the two
device tiers are drawn as separate layers in plan view (see `layermap.txt`).

## Rule set A — 3-nm-class (Si, SiGe, TMD, CNT)

| Parameter | Si / SiGe | TMD / CNT (projected) |
|---|---|---|
| Contacted gate pitch CPP | 45 | 54 |
| Gate length Lg (GATE width) | 16 | 20 |
| Metal pitch (M0, M1) | 24 | 24 |
| Nanosheet / channel width WNS | 20 | 20 |
| Nanosheets per tier | 3 | 1 monolayer / CNT array |
| S/D contact length (CT_BOT, CT_TOP) | 16 | 24 |
| Gate-to-contact space | 8 | 8 |
| Cell width (2 CPP) | 90 | 108 |
| Cell height (4 tracks) | 96 | 96 |

| Layer | Min width | Min space | Notes |
|---|---|---|---|
| NS_BOT, NS_TOP | 20 | 16 | 16 nm = single diffusion break between abutted cells |
| GATE | 16 | 29 | gate-cut 20 nm from cell top/bottom edge |
| CT_GATE | 12 | 24 | must be enclosed by GATE (>= 2 nm) |
| CT_BOT, CT_TOP | 16 | 24 | min space to GATE: 8 |
| VIA_TIER | 12 | 24 | must be enclosed by CT_BOT and CT_TOP (>= 2 nm) |
| M0 | 12 | 12 | pitch 24, horizontal preferred |
| VIA0 | 12 | 12 | must be inside M0 and M1 |
| M1 | 12 | 12 | pitch 24, vertical preferred |
| PR_BOUNDARY | — | 0 | abutting allowed |
| Marker layers | — | — | not checked |

## Rule set B — GaN exploratory (projected, ~4x scaled)

| Parameter | GaN |
|---|---|
| CPP | 200 |
| Lg | 100 |
| Metal pitch | 100 |
| Channel (2DEG fin) width | 80 |
| S/D contact length | 80 |
| Gate-to-contact space | 30 |
| Cell width (2 CPP) | 400 |
| Cell height (4 tracks) | 400 |

| Layer | Min width | Min space |
|---|---|---|
| NS_BOT, NS_TOP | 80 | 40 |
| GATE | 100 | 100 |
| CT_GATE | 50 | 100 |
| CT_BOT, CT_TOP | 80 | 80 |
| VIA_TIER | 50 | 100 |
| M0, M1 | 50 | 50 |
| VIA0 | 50 | 50 |

## DRC implemented in `make_layout.py`

* Min width: merge layer -> erode by (w/2 - tol) -> dilate back -> subtract from
  original; any residual polygon is a width violation.
* Min space: merge layer -> dilate by (s/2 - tol) -> merge -> erode -> subtract
  original; any residual is a spacing violation (fills gaps narrower than s).
* Inter-layer: GATE dilated by the gate-to-contact rule must not intersect
  CT_BOT/CT_TOP; VIA_TIER, VIA0 and CT_GATE must be enclosed by their landing
  layers (boolean NOT of via and eroded landing layer must be empty).
* All checks are run on flattened cells (inverters, 5-stage ROs, top cell), so
  abutment and routing in the ROs are verified too. tol = 0.2 nm.
