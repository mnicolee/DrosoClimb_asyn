# DrosoClimb_asyn — TODO

Last updated: 2026-09-19. Nothing has been built yet. This file records the plan and where we stopped.

**Gridding counts re-measured 2026-09-19 on 148 ClimbLogs / 444 phases.** Other counts below are from 2026-09-17 (113 ClimbLogs / 339 phases) unless marked.

---

## Where we stopped (pick up here)

### SETTLED: the output grid
- Flat **0 to 30 s**, `0.0, 0.2 … 29.8`. **150 rows per phase, always.** Never more, never less.
- No trimming of the grid, ever. The grid is built empty first; frames are placed into it.
- Any box with no frame is **NaN** and stays NaN. Including box 0.0.
- Row count never depends on frame count. Raw phases run 137–152 frames; all produce 150 rows.

### SETTLED: row 0 is not data — drop it unconditionally
Checked all 339 phases:

| row 0 | phases |
|---|---|
| all-NaN | 248 |
| has data but sits >20 px from row 1 (stale position) | 66 |
| has data, too few objects to compare — 73% NaN | 24 |
| genuinely looks like data | **1** (and it is a 0.066 s duplicate of row 1) |

- Use `.iloc[1:]` per phase. **Do not test for all-NaN** — the 91 non-NaN ones are stale positions, which is worse, since a NaN test lets them through.
- This does **not** change the row count. It removes a *frame*, not a *row*.
- **DrosoClimb already did this.** `.tail(115)` on 116 dark frames drops the first frame, which is at t=0.000 and 100% NaN, in 17 of 21 Chrimson2 files. Same operation, spelled by counting.

### RESOLVED: the "151 frames" misdiagnosis
The old note said the camera runs slightly fast. It does not — the extra frame is row 0.

| | phases with exactly 150 frames | last frame misses 29.8 by |
|---|---|---|
| counting row 0 | 65 / 339 | 0.082 s |
| **excluding row 0** | **234 / 339** | **0.018 s** |

Row-1 anchoring is closer in 239 of 339 phases. Effect on mean labelling error, all methods:

| method | with row 0 | without row 0 |
|---|---|---|
| plain relabel | 0.115 | 0.050 |
| A nearest box | 0.050 | **0.014** |
| B gaps 0.08 | 0.058 | 0.021 |
| count-first | 0.112 | 0.050 |

Dropping row 0 was the whole problem. The labelling-method argument was mostly an artefact of it.

---

## SETTLED 2026-09-19: bursts and uneven frame counts — round to nearest box
Re-measured on **148 ClimbLogs / 444 phases**. Replaces the DP / tolerance 0.15 proposal.

**What a burst is.** Not an extra frame. One frame arrives late (gap before it ~0.3 s), then the next is on time (burst gap 0.066–0.10 s, gap after 0.2 s). Long gap + burst ≈ 0.4 s in 105 of 135 bursts. 0.20% of gaps.
- Flies barely move across a burst: median 0.32 mm vs 0.98 mm for a normal 0.2 s step (same fly: 46% of its neighbouring step).
- Burst step bigger than both neighbours in only 9.8% of fly-bursts; the large ones (>10 mm) are tracker jumps, which happen at normal gaps too.
- Only 8% of bursts in the first 1 s of a phase (not 38% as previously noted).

**Rules, per phase:**
1. Drop row 0 (`.iloc[1:]`), restart the clock at row 1.
2. **Anchor on the rhythm.** In the first 5 rows, find the first regular gap (0.15–0.25 s). The frame that starts it is the anchor.
   - Round the anchor's time to its nearest box, then shift the whole phase so the anchor sits exactly on that box. Every row keeps its own X/Y; only the box label moves.
   - **Tie rule:** if the anchor's time is 0.08–0.12 s past a box (halfway), always send it to the later box, and row 1 goes to box 0.0. Otherwise plain rounding at 0.100 goes either way (floating point).
   - Example `2026-09-10_13-13-43` third phase: `0, 0.1, 0.299, 0.498` → anchor 0.1 → shift +0.1 → row 1 in box 0.0 (0.1 off), then 0.2, 0.4, 0.6.
   - 426 phases anchor on row 1 (no shift). 18 do not: 7 at ~0.1 (tie rule), 5 at ~0.133, 3 long first gaps (0.47–1.06 s, missing frames, shift ≈0.002 s), 3 short (0.066, 0.033, 0.032 — row 1 is a burst partner of row 2 and is dropped).
   - Every phase has a regular gap in its first 5 rows. After anchoring, 0 of 444 phases are off-grid.
3. Box = `np.floor(t/0.2 + 0.5)`. Not `np.round` — it rounds exact halves to even.
4. Two frames in one box: **keep the one closest to the box time**, drop the other. Nothing is pushed into a neighbouring box.
5. Empty box = NaN. Frames past box 149 are dropped.
6. `RealSeconds` (true time) is used inside the function to pick boxes, then **dropped before saving**. Output CSV has the DrosoClimb layout: `Seconds`, `ExperimentState`, `<genotype> X_n`, `<genotype> Y_n`.

**Result:**
- 150 rows per phase, always. Every kept frame within ~0.1 s of its box (mean 0.012 s, p99 0.041 s, max 0.101 s).
- 93 collisions, incl. 3 row-1 burst partners and 1 spread-out burst (24.531 / 24.698, gap 0.167).
- 95 of 66,361 frames dropped (0.14%).
- 334 NaN boxes of 66,600 (0.50%): box 0.0 never NaN, 93 at box 29.8 (camera stopping early), the rest genuine missed frames.
- In collisions the closest frame is usually the second of the pair (83 of 90 when tested before anchoring).

**Why NaN, not push.** A late frame (e.g. 27.786) was taken at 27.786, not 27.6. Putting it in 27.6 would falsely label its position. The box stays NaN.

Worked example:
```
Seconds   gap     box
24.232   0.201   24.2
24.531   0.299   24.6   kept (0.069 off)
24.698   0.167   24.6   dropped (0.098 off)
24.830   0.132   24.8
                 24.4 = NaN
```

---

## Why the grid is required at all (measured 2026-09-17)

Not cosmetic. Every downstream function indexes by **row position**.

**Cross-file clocks never match.** A compiled output is 173 flies from 21 separate recordings in one table with one `Seconds` column. Raw `Full` block first frames:
```
ClimbLog_..._14-21-41    35.765  35.965  36.164
ClimbLog_..._14-27-23    50.457  50.656  50.855
ClimbLog_..._14-34-20    37.294  37.494  37.693
```
There is no timestamp value true for all 173 flies at once. PD is the same — phases all restart at 0.000 but then diverge (0.200 / 0.200 / 0.167 / 0.200 / 0.198). To put flies from different recordings side by side you must resample onto a shared axis. That *is* the grid.

**Ungridded, `iloc[::5]` is wrong 18.8% of the time** and the error is cumulative:

| frames in a whole second | share |
|---|---|
| 4 | 9.3% |
| **5** | **81.2%** |
| 6 | 8.9% |
| 1–3 | 0.6% |

---

## The `Time` column is unusable as a bin key
- `Time == round(Seconds)` **99.9%** of rows; `== floor(Seconds)` only 51.6%.
- So 24.4 s is recorded as `Time` 24, but 24.6 s is recorded as 25.
- Use `np.floor(Seconds)` if a whole-second key is ever needed.
- Side note: DrosoClimb's `timegroup` was therefore binning `[x−0.5, x+0.5)`, not `[x, x+1)`, all along.

---

## Falls: do NOT rescale the threshold

The `-3.17` mm threshold is per-frame and only meaningful at the dt it was fitted on. Measured scaling of the negative tail over 616,982 fly-frame transitions:

| dt band | n | p5 of dY | linear prediction | ratio |
|---|---|---|---|---|
| burst <0.12 | 1,569 | −4.65 | −3.00 | 1.55 |
| **~0.2 normal** | 610,767 | −8.82 | −8.78 | 1.01 |
| ~0.4 (1 gap) | 2,790 | −7.00 | −13.19 | 0.53 |
| ~0.6 (2 gaps) | 451 | −7.82 | −23.46 | 0.33 |

Not linear. Converting to −15.85 mm/s and applying at any dt would over-flag badly on long gaps. The tail stays flat at ≈−7 to −9 mm regardless of dt because it is **tracker jumps** — per-frame errors, not per-second. Which is why the confusion matrix landed on a per-frame threshold.

**Updated 2026-09-19:** `RealSeconds` is not in the output, so no dt gate. On the grid, neighbouring filled boxes are 0.2 s apart (97.25% within 10%), and a NaN box makes `diff()` NaN on its own. So `fallso` as is, `dy = Y.diff()`, `dy < -3.17`.
- Keep a NaN `diff()` as NaN, not 0 — "couldn't tell", not "no fall". `sum(skipna=True)` with a shrinking denominator stays honest.

**Open:** the −3.17 mm threshold was fitted on DrosoClimb data. If the PD rig or arena differs it should be re-derived by the same confusion-matrix method.

**Pre-existing, not caused by gridding:** tracker jumps contaminate the fall tail at every dt including 0.2 s. 25% of bursts show >2 mm displacement, up to 60 mm — impossible for a fly, so blob identity swaps. Normal intervals reach 86 mm too.

---

## Findings that still stand (do not re-check)

**Gridding distorts speed.** 96.9% of intervals are within 10% of 0.2 s, but 0.6% are off by >20% (worst = 2×). Self-cancels over pairs (99.2% within 10% over 2 intervals). **Decided 2026-09-19: not fixed.** With the final gridding rules, 97.25% of neighbouring-box intervals are within 10% of 0.2 s, 0.43% off by >20%, true gap 0.099–0.3 s. Accepted; speed divides by 0.2 as in DrosoClimb.

**Bursts do not cluster at phase start** (2026-09-19, 148 files): 8% in the first 1 s, 13% in the first 3 s. Supersedes the old 38% / 44%.

**Burst frames barely move.** Median displacement between the two frames of a burst is 0.43 mm (42% of a normal step).

**Fewer than 150 frames = genuinely dropped frames.** Correlation with number of gaps ≥0.30 s is 0.82.

**The >80 mm/s speed filter drops the whole fly, not the frame** (`NLCLIMB.py:360-377`, inside `generation`). If a fly has ≥3 frames over 80 mm/s the entire fly is excluded. Burst artifacts therefore count toward that limit and can get a good fly thrown out. Other thresholds: fall = Y drop < −3.17 mm, pause = velocity < 2.588 mm/s.

---

## What DrosoClimb actually did (traced 2026-09-17 on SS67662 x Chrimson2)

Output is **330 rows**, `Seconds` = `np.arange(0,66,1/5)` — fabricated, verified to match exactly. It filled that fixed grid by **counting frames**, never by reading timestamps:

| block | raw frames | forced to | how |
|---|---|---|---|
| Dark | 116 | 115 | `.tail(115)` |
| Assim Full | 16 | 15 | averaged into 15 bins |
| Full | 100 | 100 | `.tail(100)` |
| Recovery | 100 | 100 | `.head(100)` |
| | | **330** | |

Then pasted the fabricated `Seconds` alongside with `concat(axis=1)`. Raw dark frames span 0.166–22.968 s; the output labels them 0.0–22.8. Row position is the only link.

**So DrosoClimb also used a fixed grid.** The only difference here is filling it by timestamp instead of by count — necessary because PD phases run 137–152 frames where Chrimson2 blocks were reliably 116.

**Only the dark block ever lost its first frame**, as a side effect of 116→115. Full and Recovery have no stale frame (0% NaN, normal 0.199 s gap) because the camera runs one continuous clock, 0→75.6 s, with no restart. PD restarts per phase, so it gets **three stale frames per file**, one per phase.

**Bursts were never a DrosoClimb problem.** 8 bursts in 6,538 gaps (0.12%) across 21 Chrimson2 files; 96.5% of gaps sit in 0.19–0.21 s. PD has roughly 10× the rate. This is why nothing in the old pipeline handles them.

**`timegroup` + `head(5)` is unsafe** and was unsafe in DrosoClimb too — only 81.2% of whole seconds contain exactly 5 frames. Do not port it.

---

## The protocol (different from DrosoClimb)
- 3 × 30 s climbing trials: `First phase`, `Second phase`, `Third phase`. No light and no assimilation phase.
- 5 fps, so each phase gives 150 rows.
- Tap-and-OK pause between phases (about 4 s); raw `Seconds` keep counting through it. **Restart the clock at 0 for each phase.**
- Filter with `df['ExperimentState'] == "First phase"` and so on. That also leaves out the one `Idle` row at the end of 23 files, so no separate drop step is needed.
- All raw ClimbLogs checked: none contain "Assimilation". The wrong `20260907\w1118 x Repo_D10` run was deleted by the user.

---

## Agreed plan

### Step 1: copy and rename (`1. Renamingfiles.ipynb`)
- **From:** `C:\Users\User\NUS Dropbox\acclab\Nicole M Lee\Raw data files\PD\<date>\<genotype>_D<age>\`
- **Raw files are never touched.** Copy only ClimbLog files, nothing else.
- **To:** `C:\Users\User\NUS Dropbox\acclab\Nicole M Lee\PD\DATA\<genotype>_<age>\`, pooling all dates.
- **New filename:** `ClimbLog_<timestamp>_<genotype>_<age>.csv`
- **Name fixes:** `Repo` becomes lowercase `repo`; w1118 always comes first, so `elav x w1118` becomes `w1118 x elav`.
- **Never overwrite** existing files in `PD\DATA`.
- **Ignore MetaData csvs** (stale). Take genotype and age from the folder name.

### Step 2: folders
- One flat level, controls included: e.g. `elav x 51375_D10`, `95240 x ddc_D20`, `w1118 x elav_D10`. No `w1118\` parent folder.

### Step 3: processing (`2. Fileprocessing.ipynb` + `NLCLIMB_asyn.py`)
- **For each phase:**
  - Filter on the phase name.
  - `.iloc[1:]` to drop row 0, then restart Seconds.
  - Anchor on the first regular gap in the first 5 rows (with tie rule), then round to the nearest box (rules above).
  - Empty boxes are NaN.
  - Exactly 150 rows per phase, always.
- Drop fly columns more than 50% empty (as in `removenans`).
- Multiply X and Y by **0.14** (confirmed).
- Columns named `<full genotype> X_1`, `<full genotype> Y_1`, e.g. `elav x 51375_D10 X_1`.
- Output one CSV per folder: `C:\Users\User\NUS Dropbox\acclab\Nicole M Lee\PD\Data Compilation\<genotype>_<age>.csv`
- Create `PD\DATA` and `PD\Data Compilation` if they don't exist.
- A genotype is the whole folder name. No driver/responder split, no w1118 lookup during processing.

### Code style (required)
- **All responses kept short, simple and direct to the point.** Bullet points, not prose. Answer only what was asked.
- Written exactly in Nicole's style: no comments, minimal markdown, no try/except.
- Same idioms as DrosoClimb `1. Renamingfiles.ipynb`, `2. Fileprocessing.ipynb` and `NLCLIMB.py` (`labcomp`/`specifiedpath`/`openPath`, `os.listdir` loops, `print("done!")`).
- Plan first, then build only on command. Nicole commits and pushes herself.

---

## Remaining steps (in order)
1. ~~Decide the gridding method~~ — settled 2026-09-19: round to nearest box, keep closest, NaN otherwise (see above).
2. Write `1. Renamingfiles.ipynb`, then do a **dry run**: list every copy and folder it would create, and confirm before copying.
3. Run step 1 and check file counts match the raw data (148 ClimbLogs as of 2026-09-19).
4. Write `NLCLIMB_asyn.py` (the `fivefps` equivalent, plus `removenans`, `onlycolsneeded`, `cleanup` adapted to 3 × 150 rows) and `2. Fileprocessing.ipynb`.
   - `RealSeconds` only inside the function; drop it before `to_csv`.
   - Do **not** port `timegroup` + `head(5)`.
   - `.iloc[1:]` per phase — no NaN check.
5. Run step 3 and check each output has 450 rows (3 × 150) and sensible NaN counts. Look at the short phase (136 real frames) specifically.
   - Old test with the DP method on `elav x 8147_D10`: 450 rows × 95 cols, 92 fly columns surviving `removenans`, 6.33% NaN. Re-check with the final rules.
6. **Later: analysis stage.**
   - Pair each experimental genotype with its controls.
   - There are **no** `w1118 x 51375`, `x 51376`, `x 8146`, `x 8147` or `w1118 x Alrm` controls; only driver-side ones (`w1118 x elav`, `w1118 x VT009792`, `w1118 x 95240`, `w1118 x ddc`, `w1118 x repo`).
7. **Later, when porting analysis functions from DrosoClimb:** genotype names contain spaces and `_D10`, so split column names **from the back**:
   - genotype: `split(" ")[0]` → `rsplit(" ", 1)[0]`
     (speedcalc, fallso, pausing, boutdisplacement, boutheight, pauseheight, boutspeed)
   - fly number: `split("_")[1]` → `split("_")[-1]`
     (boutdisplacement, boutheight, pauseheight, boutspeed, distpersec, sectioneddispchunks, positional_arguments)
   - pausenumber: `split("_")[0/1/2]` → behaviour `[-2]`, state `[-1]`, the rest is the genotype
   - deltaversion* functions: `split(" ")[1]` (WT/Expt) → `split(" ")[-1]`
     ("First phase Expt" would otherwise return "phase")
   - `filter(regex="Y.*")` / `"X_.*"` are safe as long as no genotype name contains a capital X or Y.
8. **Functions needing rewriting, not just renaming:**
   - `meangraph` (419) — mean and 95% CI across flies at each time point. **Needs the grid**, `mean(axis=1)` over flies from different recordings. Only called in `Generic line plots.ipynb`.
   - `fallcalc` (433) — **misnamed.** Returns the fraction of flies falling in each 0.2 s frame, not falls per second. `Fall_k` is a per-row 0/1 flag from `fallso`. **Needs the grid.** Only called in `Generic line plots.ipynb`.
   - `calcgraph` (396) — **does not average across flies**, no `axis=1` anywhere. Simpler than previously thought: the `-23` / `-46` are hardcoded offsets into the fabricated `arange(0,66,0.2)`. For PD it is just `Seconds` as-is, since each phase already restarts at 0.
   - `distpersec` (597) — `iloc[::5]` is safe on the grid (5 rows = 1 s). Port as is.
   - `sectioneddispchunks` (620) — exact `Seconds == nnum` match → range match. Per-fly, easy.
   - `speedcalc` (251) — `ca = 1/fps` stays; no `RealSeconds` in the output (decided 2026-09-19).
   - Port cleanly with name fixes only: `fallso`, `pausing`, `boutdisplacement`, `boutheight`, `pauseheight`, `boutspeed`, `pausenumber`, `maxvelocity`, `totalheight`.

---

## Separate todo — DrosoClimb repo, not this one
- `calcgraph` hardcodes `-23` and `-46`. These are the cumulative lengths of the preceding phases (Dark, then Dark + Full). Should be computed from the phase lengths, not typed in.
- `timegroup` + `head(5)` mis-bins ~18.8% of seconds and bins `[x−0.5, x+0.5)` because `Time` rounds rather than floors. Pre-existing issue in the published pipeline.

---

## Done elsewhere on 2026-09-15 (for reference)
- DrosoClimb: default branch renamed back to `main`, local folder `deltaG_screen` renamed to `DrosoClimb`, Correlation-heatmap deleted.
- `jonnysmagic` renamed to `timegroup` in DrosoClimb main, Dev and Dev_AsOPN3, and CLOSAR main. Dev_YM and PCA untouched.
  - **All committed and pushed** — verified 2026-09-16: main, Dev, Dev_AsOPN3 and CLOSAR/main all 0 ahead / 0 behind origin.
- A GitHub Desktop stash conflict on DrosoClimb main was fixed. The old 2024-11-20 stash is kept as `stash@{0}: backup: old 2024-11-20 main stash`.
