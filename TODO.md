# DrosoClimb_asyn — TODO

Last updated: 2026-09-21. Steps 1–5 done. Next: the analysis notebook.

Counts measured on 148 ClimbLogs / 444 phases.

---

## Protocol

- 3 × 30 s climbing trials: `First phase`, `Second phase`, `Third phase`. No light, no assimilation.
- 5 fps, 150 rows per phase. Tap-and-OK pause (~4 s) between phases; raw `Seconds` run through it, so the clock restarts per phase.
- Filtering on the phase name also drops the trailing `Idle` row (present in 30 files).

---

## Done

### Step 1 — `1. Renamingfiles.ipynb`
Copies ClimbLogs from `Raw data files\PD\<date>\<genotype>_D<age>\` to `PD\DATA\<genotype>_<age>\`, pooling dates. Raw never modified, never overwrites, MetaData ignored. 148 files, 36 genotype folders.

Name fixes were applied **in the raw data**, not in code:
- `VT0009792` → `VT009792`
- `elav x w1118` → `w1118 x elav`
- `95240 x ddc` / `95240 x repo` → `ddc x 95240` / `repo x 95240` (95240 goes last)

### Step 2 — `NLCLIMB_asyn.py` + `2. Fileprocessing.ipynb`
Output: `PD\Data Compilation\<genotype>_<age>.csv`, 36 files, 450 rows each.

Gridding, per phase:
1. Drop row 0 (`.iloc[1:]`), restart the clock.
2. Anchor on the first regular gap (0.15–0.25 s) in the first 5 rows; the frame that starts it is the anchor. Shift the phase so the anchor sits on its nearest box; an exact halfway takes the **lower** box.
3. Box = nearest 0.2. Two frames in one box → keep the closer, omit the other. Never pushed to a neighbour.
4. Empty box = NaN. Frames outside 0.0–29.8 omitted.
5. `RealSeconds` used internally, dropped before saving.

Result: 426 phases need no shift, 18 do. Every kept frame within 0.099 s of its box. 101 frames omitted of 66,361 (0.15%). 340 NaN boxes of 66,600 (0.51%). Box 0.0 never NaN.

`removenans` runs cumulatively across all three phases, as in DrosoClimb. 2516 flies → 1822.

### Step 3 — `NLMATH_asyn.py`
Metrics chosen: **overall speed, bout speed, total height, straightness index**, plus the line plots.

Ported: `generation`, `separation`, `fallso`, `pausing`, `speedcalc` (in `NLCLIMB_asyn.py`); `calcgraph`, `velodabest`, `ospeed`, `boutspeed`, `bspeed`, `refine`, `totalheight`, `straightnessindexmeter`, `distpersec`, `disppersec`, `sectioneddispchunks`, `meangraph`, `fallcalc` (in `NLMATH_asyn.py`).

Not ported: `timegroup`, `mixedfps`, `frames`, `trans`, `control`, `fivesecondrule`.

Changes applied throughout:
- `Dark`/`Full`/`Recovery` → the three phase names; `'Assimilation time - '` filters removed.
- Genotype names contain spaces and `_D10`, so splits count from the back: `split(" ")[0]` → `rsplit(" ", 1)[0]`, `split("_")[1]` → `split("_")[-1]`.
- `generation`: `.iloc[:-4]` removed (no trailing second to trim); `23*fps` → `firstphase_len = fps*30`; `int(output)` → `int(output.iloc[0])` to clear a FutureWarning, output verified identical.
- `fallso` and `pausing`: a NaN stays NaN rather than becoming 0 — "couldn't tell", not "no fall".
- `calcgraph`: the `-23` / `-46` lines removed, since each phase already restarts at 0.
- `straightnessindexmeter`: all three phases (DrosoClimb did only two).

Shortened functions are listed in `CHANGES.md`.

---

## Next

1. Write the `Generic line plots` equivalent. Load a genotype and its control, `drop(dfe.columns[[0]])` (the CSVs carry an index column), `generation` on both — no `fivesecondrule` — then the metrics.
2. Check the metrics across all 36 genotypes, not just the few tested.
3. Pair each experimental genotype with its controls.

### Control pairings
23 experimental, 13 control. 8 have both parental controls; 15 have only the driver side. There are **no** `w1118 x 51375`, `x 51376`, `x 8146`, `x 8147` or `w1118 x Alrm` controls.

---

## Findings — do not re-check

- **Row 0 is not data.** Of 339 phases, 248 were all-NaN and 66 held a stale position >20 px from row 1. Only 1 looked genuine, and it was a duplicate. Drop it unconditionally — a NaN test lets the stale ones through. This also resolved the old "151 frames" misdiagnosis: the camera does not run fast, the extra frame was row 0.
- **The grid is required.** Cross-file clocks never match — a compiled output holds flies from 21 recordings under one `Seconds` column. Ungridded, `iloc[::5]` is wrong 18.8% of the time and the error accumulates.
- **Bursts.** One frame late (~0.3 s gap), the next on time (0.066–0.10 s). 0.20% of gaps. Flies barely move across one (median 0.32 mm vs 0.98 mm for a normal step). They do not cluster at phase start (8% in the first 1 s).
- **Gridding distorts speed slightly.** 97.25% of neighbouring-box intervals within 10% of 0.2 s, 0.43% off by >20%. Accepted; speed divides by 0.2.
- **Falls: do not rescale the threshold.** The `-3.17` mm cut is per-frame, not per-second — the negative tail stays flat at ≈−7 to −9 mm at every dt because it is tracker jumps, not real falls. On the grid, `dy = Y.diff()`, `dy < -3.17`, no dt gate.
- **Tracker jumps are pre-existing**, not caused by gridding. 25% of bursts show >2 mm displacement, up to 60 mm; normal intervals reach 86 mm too. The 80 mm/s filter is what catches them.
- **The `Time` column is unusable as a bin key.** `Time == round(Seconds)` 99.9% of rows but `== floor(Seconds)` only 51.6%.
- **No clock drift.** Mean offset 0.0104 s early in a phase, 0.0145 s late; 0 of 444 phases drift more than 0.02 s. One anchor holds for 30 s.
- **Data is clean structurally.** All 148 files have the 3 phases, each one contiguous block, always 17 objects, no box ever had 3+ frames competing.
- **What DrosoClimb did.** Also a fixed grid (330 rows, `arange(0,66,1/5)`), but filled by counting frames rather than reading timestamps — `.tail(115)`, `.tail(100)`, `.head(100)`. Necessary here to fill by timestamp because PD phases run 137–152 frames. `timegroup` + `head(5)` was unsafe there too (only 81.2% of whole seconds hold exactly 5 frames) — not ported.

---

## Open

- `-3.17` (falls) and `2.588` (pauses) were fitted on the DrosoClimb rig. Same rig, so they hold — but they are the two numbers to revisit if the arena changes.
- The 80 mm/s filter counts ≥3 bad frames across all 450 rows, where DrosoClimb had 330. Proportionally stricter. Left as is.
- When porting further analysis functions, the same split-from-the-back fixes apply to `boutdisplacement`, `boutheight`, `pauseheight`, `boutspeed`, `pausenumber`, `sectioneddispchunks`, `positional_arguments`, and the `deltaversion*` functions (`split(" ")[1]` → `split(" ")[-1]`).
- `filter(regex="Y.*")` / `"X_.*"` stay safe only while no genotype name contains a capital X or Y. None of the 36 do.

---

## Separate — DrosoClimb repo, not this one

- `calcgraph` hardcodes `-23` and `-46`, the cumulative lengths of the preceding phases. Should be computed, not typed.
- `timegroup` + `head(5)` mis-bins ~18.8% of seconds, and bins `[x−0.5, x+0.5)` because `Time` rounds rather than floors.
