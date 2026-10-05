# refs.bib verification notes

Date: 2026-10-05. Companion to `refs.bib` for the TED manuscript
"A Unified Physics-Based Compact-Model and Circuit-Validation Flow for
Multi-Material CFET Logic: Si, SiGe, MoS2/WSe2, CNT and GaN".

## How entries were verified

The sandbox egress proxy blocked direct API access to OpenAlex, Crossref,
Semantic Scholar, doi.org, IEEE Xplore, nature.com, arXiv, PubMed and
Europe PMC, so the `paper-search` skill (OpenAlex) could not be used.
Every entry was instead cross-checked through web search against at least
one independent public bibliographic record (publisher landing page,
IEEE Xplore / NASA ADS / Semantic Scholar listing, or an institutional
repository). Title, first author, venue, year and DOI were confirmed for
every entry; volume/issue/pages were confirmed where they appear below.
Full author lists are included only where a record enumerated them; where
only the leading authors were confirmed the entry uses `and others`
(rendered as "et al." by IEEEtran).

## Key mapping against the requested list

| # | Requested key(s)                   | Key used            | Status |
|---|------------------------------------|---------------------|--------|
| 1 | IRDS2023                           | `IRDS2023`          | Verified. 2023 edition, More Moore chapter PDF URL confirmed. |
| 2 | Loubet2017                         | `Loubet2017`        | Verified. VLSIT 2017, pp. T230-T231, DOI 10.23919/VLSIT.2017.7998183. First 10 authors confirmed; remainder `and others`. |
| 3 | Ryckaert2018 / Subramanian2020     | both                | Verified. VLSIT 2018 pp. 141-142, DOI 10.1109/VLSIT.2018.8510618; VLSIT 2020 pp. 1-2, DOI 10.1109/VLSITechnology18217.2020.9265073. Full author lists confirmed. |
| 4 | Vincent2020 / Huang2020            | `Huang2020`         | Verified. Intel IEDM 2020 "3-D self-aligned stacked NMOS-on-PMOS nanoribbon transistors", pp. 20.6.1-20.6.4, DOI 10.1109/IEDM13553.2020.9372066. No imec paper with "Vincent" as first author on CFET DTCO could be located; Ryckaert2018 (which includes B. Vincent as co-author) already covers the imec DTCO argument. |
| 5 | Mertens2016                        | `Mertens2016`       | Verified. VLSIT 2016 pp. 1-2, DOI 10.1109/VLSIT.2016.7573416. Full author list confirmed. |
| 6 | Mochizuki2020                      | `Mochizuki2020`     | Verified. IEDM 2020 pp. 2.3.1-2.3.4, DOI 10.1109/IEDM13553.2020.9372041. |
| 7 | Li2023Nature                       | `Li2023Nature`      | Verified. Note the real title is "...two-dimensional **semiconductor** contacts" (not "transistor contacts"). Nature 613, 274-279 (2023), DOI 10.1038/s41586-022-05431-4. The abstract reports Rc = 123 ohm-um and Ion = 1135 uA/um on monolayer MoS2; the ~42 ohm-um figure quoted in the manuscript draft should be checked against the paper body (it is the quantum-limit value discussed there), not the abstract. |
| 8 | Shen2021                           | `Shen2021`          | Verified. Nature 593(7858), 211-217, DOI 10.1038/s41586-021-03472-9. |
| 9 | OBrien2023 / Intel2D               | `OBrien2021`, `OBrien2023` | Verified. IEDM 2021 pp. 7.1.1-7.1.4, DOI 10.1109/IEDM19574.2021.9720651 (full list confirmed); Nat. Commun. 14, 6400 (2023), DOI 10.1038/s41467-023-41779-5 (first five authors confirmed, rest `and others`). Intel IEDM 2024 2D GAA paper was not pursued since these two already cover the Intel 2D line. |
|10 | Chou2021                           | `Chou2022`          | Verified. The WSe2 p-FET record paper is IEDM **2022** (not 2021): "High-performance monolayer WSe2 p/n FETs via antimony-platinum modulated contact technology...", pp. 7.2.1-7.2.4, DOI 10.1109/IEDM45625.2022.10019491. Only the first author was confirmed, so `and others` is used. (Chou's IEDM 2021 paper is on Sb contacts to MoS2, DOI 10.1109/IEDM19574.2021.9720608 -- not added, but available if needed.) |
|11 | Cao2019 / Nature2DCompact          | `Pasadas2019`       | Verified. DOI 10.1038/s41699-019-0130-6 resolves to Pasadas et al., "Large-signal model of 2DFETs: compact modeling of terminal charges and intrinsic capacitances", npj 2D Mater. Appl. 3, 47 (2019). The requested title/first author ("Cao", "Physics-based compact model") did not match; the key was renamed accordingly. |
|12 | Liu2020Science                     | `Liu2020Science`    | Verified. Science 368(6493), 850-856, DOI 10.1126/science.aba5980. Full author list confirmed. |
|13 | Hills2019                          | `Hills2019`         | Verified. Nature 572(7771), 595-602, DOI 10.1038/s41586-019-1493-8. |
|14 | Deng2007                           | `Deng2007`          | Verified. TED 54(12), 3186-3194, DOI 10.1109/TED.2007.909030 (Part I). Part II not added. |
|15 | Bader2020                          | `Bader2020`         | Verified. TED 67(10), 4010-4020, DOI 10.1109/TED.2020.3010471. Full author list confirmed. |
|16 | Chowdhury2020 / Zheng2021          | both                | Verified. Zheng et al., Nat. Electron. 4, 595-603 (2021), DOI 10.1038/s41928-021-00611-y; Chowdhury et al., EDL 41(6), 820-823 (2020), DOI 10.1109/LED.2020.2987003 (first demonstration of complementary logic operating at 300 C). |
|17 | Amano2018                          | `Amano2018`         | Verified. J. Phys. D 51(16), 163001, DOI 10.1088/1361-6463/aaaf9d. ~70 authors; first six listed then `and others`. |
|18 | Enz1995                            | `Enz1995`           | Verified. AICSP 8(1), 83-114, DOI 10.1007/BF01239381. |
|19 | Lundstrom2002 / Natori1994         | `Lundstrom2002`     | Verified. TED 49(1), 133-141, DOI 10.1109/16.974760. Natori 1994 not added. |
|20 | Vogt2022 / Ngspice, OpenVAF        | `Ngspice`, `OpenVAF`| Verified. Ngspice manual v42 is dated **Dec. 27, 2023** (not 2024); authors Vogt, Atkinson, Nenzi; URL confirmed. Newer manuals (v43 Jul 2024 ... v47 Aug 2026) exist -- change the version/year to match the ngspice build actually used. `OpenVAF` cites Kuthe, Mueller, Schroeter, IEEE JEDS 8, 1416-1423 (2020), DOI 10.1109/JEDS.2020.3023165 (VerilogAE, the predecessor of OpenVAF; there is no peer-reviewed OpenVAF paper that could be verified). |
|21 | CadenceVerilogA                    | `CadenceVerilogA`, `CadenceSpectre` | Manuals. Verilog-A Language Reference (Product Version 13.1.1, Apr. 2014 is the latest version found in public mirrors) and Spectre Circuit Simulator Reference (Product Version 19.1, Jan. 2020). Update the version strings to the release you used. |
|22 | Chauhan2015 / BSIMCMG              | `Chauhan2015`       | Verified. Academic Press, 2015, ISBN 978-0-12-420031-9. Author spelling follows IEEE/BSIM group usage (Venugopalan, Paydavosi); the publisher's listing misspells these as "Vanugopalan"/"Payvadosi". |
|23 | Yakimets2017 / Schuddinck          | `Yakimets2017`      | Verified. IEDM 2017 pp. 20.4.1-20.4.4, DOI 10.1109/IEDM.2017.8268429. Full author list confirmed. |
|24 | Lee2023GaNRO                       | `Zheng2021GaNRO`    | Verified substitute. No "Lee 2023" GaN RO paper could be located. Used Zheng et al., "Monolithically integrated GaN ring oscillator based on high-performance complementary logic inverters", IEEE EDL 42(1), 26-29 (2021), DOI 10.1109/LED.2020.3039264. Author order of the middle co-authors (Zhang/Yang/Wei) is from ADS and should be eyeballed against the PDF. For high-temperature GaN CMOS use `Chowdhury2020`. |
|25 | Kim2023CNTCFET                     | `Shulaker2017`      | Verified substitute. Nature 547(7661), 74-78, DOI 10.1038/nature22994. No verifiable "CNT CFET" paper with that key was found. |
|26 | Cadence2024Training                | `Cadence2024Training` | Manual (Virtuoso ADE Explorer / Assembler user guides, IC23.1). URL is the Cadence product page; not a DOI-bearing document. |

## Items NOT included (could not be verified or not needed)

- `Vincent2020` -- no imec CFET DTCO paper with Vincent as first author found.
- `Natori1994` -- not needed once Lundstrom2002 was verified; not added.
- `Lee2023GaNRO`, `Kim2023CNTCFET` -- no real papers matching these
  placeholder keys were found; verified substitutes listed above.
- Intel IEDM 2024 2D GAA paper -- not searched for; OBrien2021/2023 cover
  the Intel 2D line.
- "OpenVAF" peer-reviewed paper -- none exists; VerilogAE (Kuthe 2020) is
  the citable antecedent. If the OpenVAF binary is cited, add a @misc with
  the project URL after confirming the repository is reachable.

## Things to double-check before submission

1. Chou2022 and OBrien2023 author lists are truncated (`and others`);
   expand from the PDFs if the journal style requires full lists.
2. Ngspice manual version/year must match the simulator build used.
3. Cadence manual product versions should match the installed release.
4. Journal issue numbers for Nature/Science entries were taken from
   secondary listings; IEEEtran does not print them, so they are harmless
   if slightly off, but verify if switching to a style that does.
