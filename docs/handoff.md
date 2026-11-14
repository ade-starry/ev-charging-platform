# Handoff — current project state

**Purpose:** a fresh session (or a teammate) should be able to pick this project up from this
file alone.

**Last updated:** 2026-11-14

---

## 1. What is decided (do not re-litigate)

| Decision | Value | Decided by |
|---|---|---|
| Repository | **public** — upstream https://github.com/blkmanba1/ev-charging-platform; current work on the `ade-starry` fork, branch `sp4/initial-dashboard` | team |
| Task board | Trello, card list in `docs/trello-board.md` | team |
| Team comms | **QQ group, students only** | team |
| Comms with supervisor | Teams meetings + email | team |
| Datasets | **Official US municipal open data** — City of Boulder (primary) + City of Palo Alto (validation); the supervisor accepts either Chinese or US data | team + supervisor |
| Time resolution | **1 hour** | team |
| Currency | **CNY (¥)** for SP4's Chinese tariff test fixtures; contract amendment **A1** records that neither US dataset contains tariff data and the final reporting currency is TBD | team |
| Storage timezone | **UTC** (display handled by SP4) | team |
| Scenario hand-off | **CSV** | team |

Full detail: `docs/integration-contract.md`.

## 2. Meeting logistics

- Recurring: **every two weeks on Saturday** through 2027-06-13.
- Platform: Microsoft Teams (link and passcode are in the calendar invitation — deliberately
  **not** stored in this public repo).
- Recent confirmed meetings: **2026-09-19, 2026-10-03, 2026-10-17** (see the SP4 logbook).
  **Confirm the next date/time with the supervisor** rather than assuming the cadence is unchanged.
- The supervisor's kickoff email said "this Friday" but signed off "See you Saturday"; the
  `.ics` attachment said Saturday 26 September. Confirm dates directly with him.

## 3. Team & ownership

Status as of **2026-11-14**:

| Sub-project | Owner | Directory | Status |
|---|---|---|---|
| SP1 — Data Analysis & Demand Forecasting | Xu Yuxuan | `subprojects/sp1-data-forecasting/` | **Phase 1 complete** — US datasets secured (Boulder primary, Palo Alto validation), DST-safe pipeline, forecast and baseline outputs, **79 tests passing** |
| SP2 — Smart Charging Scheduling | Xie Letian | `subprojects/sp2-smart-scheduling/` | not started |
| SP3 — Renewable-Aware Charging Management | **unallocated** | `subprojects/sp3-renewable-aware/` | not started |
| SP4 — Monitoring & Visualisation Platform | Li Chunren | `subprojects/sp4-monitoring-dashboard/` | **Dashboard prototype** — SP1 forecast ingestion, contract-compliant cost engine, labelled demo snapshot, **25 tests passing** |
| SP5 — Economic, Environmental & System Assessment | He Zimo | `subprojects/sp5-system-assessment/` | not started |

## 4. Open items

1. **SP3 owner** — the official brief says five students; only four are assigned. Asked of the
   supervisor; awaiting an answer.
2. **Aggregate vs per-EV forecast** — SP1 currently forecasts **aggregate** demand. Boulder has no
   vehicle identifier, but **Palo Alto does** (`User ID`, 97% populated), so a per-EV variant is
   possible without new data — it is a scope decision, not a data limitation. Confirm with the
   supervisor.
3. **Carbon intensity source** for SP5's baseline — the Chinese route is closed with the data
   decision. Options are recorded in `data/README.md` (e.g. keyless NESO Carbon Intensity API);
   needs a decision and a citable reference.
4. **Shared tariff table** (recommendation: SP2) — still a blocker: the Boulder/Palo Alto data
   contain no tariff column. The source survey is in `docs/tariff-sources.md`, with artefacts in
   `data/raw/tariff/`: Boulder 2018–2023 uses OpenEI URDB (bulk CSV, no key) for the ToU period
   mapping and Xcel's rate-summary PDFs for all-in $/kWh. **Decided 2026-09-22:** Palo Alto is
   priced on its tiered residential E-1 schedule and declared out of ToU scope, so the
   peak-shifting demonstration runs on Boulder and SP5 reports the two sites separately. See
   contract amendment **A1**.
5. **Timezone and tariff alignment in SP4** — `config.yaml` uses `America/Denver` for SP1's dataset
   processing, while SP4's dashboard currently displays `Asia/Shanghai` and quotes Chinese tariffs
   as test fixtures. Revisit when US tariffs are added to SP4.
6. **Assessment 1** — the 8-page report, ECD, risk assessment and first logbook were prepared in
   the local workspace `report/` for the **2026-10-30** deadline. Submission receipt is not
   recorded in this repository; confirm it with the student.

## 5. Where to start implementing

Read in this order:

1. `README.md` — scope, team, data flow
2. `docs/integration-contract.md` — **the interfaces; read before writing any output file**
3. `CONTRIBUTING.md` — branching, commits, definition of done
4. Your own `subprojects/spN-*/README.md`

SP1's outputs are already contract-compliant, so **SP2 and SP4 can develop against real files
today**:

```bash
python subprojects/sp1-data-forecasting/scripts/fetch_datasets.py --dataset us-boulder-ev
python subprojects/sp1-data-forecasting/scripts/run_sp1.py --dataset us-boulder-ev
# -> data/processed/sp1-demand-forecast-v1.csv      (+ .meta.json)
# -> data/processed/sp1-baseline-demand-v1.csv      (+ .meta.json)  "everyone plugs in at 18:00 local"

python -m streamlit run subprojects/sp4-monitoring-dashboard/dashboard.py
```

Substitute `us-palo-alto-ev` for the validation site. The Chinese dataset keys
(`cn-charging-orders-*`) remain in `datasets.yaml` only for comparison and test fixtures.

Phase 1 (Months 1–2) status:

| SP | Phase 1 task | Status |
|---|---|---|
| SP1 | Identify and clean the official US datasets | **done** — see `subprojects/sp1-data-forecasting/README.md` |
| SP2 | Tariff research and the ToU recipe | **partly done** — source survey in `docs/tariff-sources.md`; scheduling not started |
| SP3 | Solar resource data + PV modelling (pending owner) | to do |
| SP4 | Development environment and dashboard prototype | **done** — Streamlit dashboard with SP1 ingestion and cost engine |
| SP5 | Cost and gCO₂/kWh baseline | to do |

## 6. Things easily forgotten

- **Datasets are git-ignored** (`data/raw`, `data/interim`, `data/processed`). Record every
  dataset in `data/README.md` in the same PR.
- **The repo is public.** No datasets, credentials, or meeting links in commits.
- **A decision made in QQ does not exist until it is in the repository.**
- `data/README.md` contains the researched source lists. The **team decision is the US municipal
  datasets** (Boulder primary, Palo Alto validation); the Chinese candidates are kept as
  historical context and for SP4's test fixtures.
- **Neither US dataset contains a tariff column.** Boulder is priced from OpenEI URDB + Xcel
  rate-summary PDFs; Palo Alto is tiered E-1 and out of ToU scope. The Chinese tariffs currently
  in SP4 are **test data only** — the supervisor advised using overseas tariffs for the final
  evidence.
- The merged evaluation documents are in `docs/literature-review/` (21 DOI-verified references)
  and `docs/phase1-report/` (SP1 Phase-1 report, PDF and LaTeX sources).

## 7. Source material (workspace, not in the repo)

| File | Contents |
|---|---|
| `RE_ Missed you at today's meeting - let's reschedule.eml` | Supervisor's kickoff email + the earlier "nobody joined" email |
| `EV_Charging_Project_Description.pdf` | Official brief: 5 sub-projects, outcomes, prerequisites |
| `ATT00003.ics` | Calendar invitation with the recurring Teams meeting |
| `毕设资料整理.md` | Chinese-language summary of all three, with contradictions flagged |
| `回复导师邮件草稿.md` | English reply draft, two open questions |

## 8. Delivery targets (from the official brief)

EV charging dataset repository and analysis framework · ML demand forecasting model · smart
charging scheduling algorithms · renewable-aware charging module · monitoring & visualisation
dashboard · economic/environmental/sustainability assessment reports · integrated software
prototype · final technical report, dissertation, and presentation.

Milestones: **M1** literature review + clean datasets (Months 1–2) · **M2** mid-project report,
subsystems work on mock data (Months 3–4) · **M3** fully working integrated prototype (Month 5) ·
**M4** thesis submitted and viva passed (Months 6–7).
