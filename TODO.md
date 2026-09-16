# DrosoClimb_asyn — TODO

Last updated: 2026-09-16. Nothing has been built yet. This file records the plan and where we stopped.

---

## Where we stopped (pick up here)

**Open decision: how to turn raw frame times into fixed 0.2 s labels (0.0, 0.2 … 29.8).**

Four methods were tested on all 91 PD ClimbLogs (273 phases, 40,589 gaps).

| method | how | mean err | max err | frames dropped | NaN | phases ending at box 149 |
|---|---|---|---|---|---|---|
| plain relabel (DrosoClimb style) | number frames 0…149 in order | 0.069 s | **2.809 s** | 0 | 0 | 146 / 273 |
| A — nearest box | `round(t / 0.2)` | **0.022 s** | **0.100 s** | 156 | 213 | 197 / 273 |
| B — follow the gaps | `cumsum(round(gap / 0.2))` | 0.030 s | 0.463 s | 116 | 151 | 187 / 273 |
| B with burst threshold **0.08** | same, better cutoff | 0.025 s | 0.231 s | 83 | 151 | 187 / 273 |
| count-first (Nicole's) | fix count to 150, then relabel | 0.051 s | 0.816 s | **52** | 140 | **273 / 273** |

**Still not decided.** The trade is now clear:

- **A / B get the timing right** — a frame ends up in the correct row
- **count-first gets the structure right** — every phase is exactly 150 rows ending at 29.8 s
- A's cost is collisions (deletes real frames); B's cost is drift (loses count)

**Cost is not a factor.** All methods run in 0.6–2.8 ms across the whole dataset, against 882 ms just reading the CSVs.

### Both failure modes come from the same event
A frame arrives late (~0.3 s gap), then the next arrives early (~0.13 s) to catch up. The pair spans 0.4 s = 2 boxes.
- **B reads this correctly** (1 box + 1 box)
- **A collides them** — both round to the same box, so one real frame is deleted. Happens 45 times.

Real example, `elav x 8147_D10\...11-29-08.csv`, Second phase:
```
row   Seconds   gap     A box   B box
121   24.232    0.201   24.2    24.0   <- B has drifted a full box
122   24.531    0.299   24.6    24.2   <- A collides these two
123   24.698    0.167   24.6    24.4
```

---

### Findings (measured 2026-09-16, don't re-check)

**Burst threshold should be 0.08 s, not 0.10 s.** There is an empty valley in the gap histogram:
```
0.000-0.050 :  37      0.080-0.095 :   0   <- nothing here
0.050-0.080 :  46      0.095-0.105 :  64   <- a separate population
                       0.105-0.150 :  93
```
The 0.10 cutoff splits that second cluster arbitrarily (33 below / 31 above). Moving to 0.08 drops **33 fewer real frames AND improves accuracy** — mean 0.030 → 0.025 s, phases >0.2 s off at the end 13 → 2. The ~0.30 s rounding problem fixes itself once the paired frame takes its own box.

**Frame counts per phase are not 150.**
| n | 136 | 145 | 146 | 147 | 148 | 149 | **150** | 151 | 152 |
|---|---|---|---|---|---|---|---|---|---|
| phases | 1 | 1 | 7 | 7 | 12 | 48 | **146** | 50 | 1 |

- Exactly 150: 53%. Within 149–151: 89%.
- **151 frames usually does NOT mean a burst** — only 24 of 50 have one. The camera just runs slightly fast.
- **Fewer than 150 = genuinely dropped frames.** Correlation with number of gaps ≥0.30 s is 0.82; 69 of 76 short phases still ran the full ~29.7 s.
- 16 phases have a burst *and* exactly 150 frames — 15 of those also have a missing frame, so the count cancels out. Plain relabel error on these is 0.221 s vs 0.131 s on clean phases.

**Bursts cluster at phase start.** 38% in the first 1 s, 44% in the first 3 s; the rest spread evenly. Same in all three phases (28 / 32 / 30), so it recurs at every tap-and-OK restart. Dropped frames show no such clustering.

**Burst frames barely move.** Median displacement between the two frames of a burst is 0.43 mm (42% of a normal step — proportional to the shorter dt). So which one you keep hardly matters. Keeping the later frame is wrong 49% of the time; "keep whichever is closest to the box" is free and better (mean err 0.088 → 0.051 s).

**Gridding distorts speed.** 96.9% of intervals are within 10% of the assumed 0.2 s, but 0.6% are off by >20% (worst = 2×). Self-cancels over pairs (99.2% within 10% over 2 intervals). **Fix: output a `RealSeconds` column alongside `Seconds`** and use it for speed/displacement denominators.

**CORRECTION — the first row is not always empty.** It is all-NaN in **201 of 273** phases, not all of them. Check per phase, don't assume.

**CORRECTION — earlier clash counts superseded.** The old note said 97 bursts / 81 phases affected. Measured: 116 bursts at threshold 0.10, 83 at 0.08; A collides in 23 phases. Direction of the conclusion unchanged.

**28–38 phases produce more than 150 boxes** and get truncated, depending on method.

### DrosoClimb has nothing to reuse for this
Checked `main`, `Dev`, `Dev_AsOPN3`. The old pipeline **never mapped timestamps to labels**:
- `np.arange(0,66,1/5)` (`NLCLIMB.py:60`) is manufactured and `concat(axis=1)`-ed alongside the frames. Alignment came purely from row position.
- `Seconds.diff().mean()` is only used to pick fps 5 vs 1.
- `round(Seconds,1)` in `distpersec` runs on the already-manufactured column, not raw timestamps.

**`timegroup` + `head(5)` is unsafe here** — and was unsafe in DrosoClimb too. Only **88.2%** of whole seconds contain exactly 5 frames in this data:
```
1 frame: 41   2: 48   3: 69   4: 177   5: 3272   6: 101  (seconds)
```
So `head(5)` mis-binned ~11.8% of seconds — dropping a real 6th frame, or passing 4 through and shifting everything after. Pre-existing issue in the published pipeline, noted separately.

**The >80 mm/s speed filter exists but drops the whole fly, not the frame** (`NLCLIMB.py:360-377`, inside `generation`). If a fly has ≥3 frames over 80 mm/s the entire fly is excluded. Burst artifacts therefore count toward that limit and can get a good fly thrown out. Other thresholds: fall = Y drop < −3.17 mm, pause = velocity < 2.588 mm/s.

**Tracker jumps exist independently of this decision.** 25% of bursts show >2 mm displacement, up to 60 mm — impossible for a fly in 66 ms, so blob identity swaps. Normal intervals reach 86 mm too.

---
## The protocol (different from DrosoClimb)
- 3 × 30 s climbing trials: `First phase`, `Second phase`, `Third phase`. No light and no assimilation phase.
- 5 fps, so each phase should give 150 rows.
- There's a tap-and-OK pause between phases (about 4 s), and the raw `Seconds` keep counting through it. **Restart the clock at 0 for each phase.**
- Filter with `df['ExperimentState'] == "First phase"` and so on. That also leaves out the one `Idle` row at the end of 23 files, so no separate drop step is needed.
- All 91 raw ClimbLogs were checked: none contain "Assimilation". The wrong `20260907\w1118 x Repo_D10` run was deleted by the user.

---

## Agreed plan

### Step 1: copy and rename (`1. Renamingfiles.ipynb`)
- **From:** `C:\Users\User\NUS Dropbox\acclab\Nicole M Lee\Raw data files\PD\<date>\<genotype>_D<age>\`
- **Raw files are never touched.** Copy only ClimbLog files, nothing else.
- **To:** `C:\Users\User\NUS Dropbox\acclab\Nicole M Lee\PD\DATA\<genotype>_<age>\`, pooling all dates.
- **New filename:** `ClimbLog_<timestamp>_<genotype>_<age>.csv`
- **Name fixes:**
  - `Repo` becomes lowercase `repo`.
  - w1118 always comes first: `elav x w1118` becomes `w1118 x elav`.
- **Never overwrite** existing files in `PD\DATA`.
- **Ignore MetaData csvs** (stale). Take genotype and age from the folder name.

### Step 2: folders
- One flat level of folders, controls included: e.g. `elav x 51375_D10`, `95240 x ddc_D20`, `w1118 x elav_D10`. No `w1118\` parent folder.

### Step 3: processing (`2. Fileprocessing.ipynb` + `NLCLIMB_asyn.py`)
- **For each phase:**
  - Filter on the phase name.
  - Restart Seconds.
  - Place frames on 0.2 s labels (**method still open, see top**).
  - Bursts < 0.1 s: keep the later frame.
  - Missing labels are NaN.
  - Exactly 150 rows per phase.
- Drop fly columns that are more than 50% empty (as in `removenans`).
- Multiply X and Y by **0.14** (confirmed).
- Columns are named `<full genotype> X_1`, `<full genotype> Y_1` (option a), e.g. `elav x 51375_D10 X_1`.
- Output is one CSV per folder: `C:\Users\User\NUS Dropbox\acclab\Nicole M Lee\PD\Data Compilation\<genotype>_<age>.csv`
- Create `PD\DATA` and `PD\Data Compilation` if they don't exist.
- A genotype is the whole folder name. There's no driver/responder split, and no w1118 lookup during processing.

### Code style (required)
- **All responses are to be kept short, simple and direct to the point.** Bullet points, not prose. Answer only what was asked.
- Written exactly in Nicole's style: no comments, minimal markdown, no try/except.
- Same idioms as DrosoClimb `1. Renamingfiles.ipynb`, `2. Fileprocessing.ipynb` and `NLCLIMB.py` (`labcomp`/`specifiedpath`/`openPath`, `os.listdir` loops, `print("done!")`).
- Plan first, then build only on command. Nicole commits and pushes herself.

---

## Remaining steps (in order)
1. **Decide the labelling method** (top of this file). Then settle the burst rule: threshold **0.08 s**, keep whichever frame is closest to its box.
2. Write `1. Renamingfiles.ipynb`, then do a **dry run**: list every copy and folder it would create, and confirm before copying.
3. Run step 1 and check that the file counts match the raw data (91 ClimbLogs).
4. Write `NLCLIMB_asyn.py` (the new `fivefps` equivalent with the chosen method, plus `removenans`, `onlycolsneeded`, `cleanup` adapted to 3 × 150 rows) and `2. Fileprocessing.ipynb`.
   - Add a **`RealSeconds`** column so speed/displacement can use true dt.
   - Do **not** port `timegroup` + `head(5)`.
   - Check the first row per phase for all-NaN; do not assume it is empty.
5. Run step 3 and check that each output has 450 rows (3 × 150) and sensible NaN counts. Look at the short file (136 real frames) specifically.
6. **Later: analysis stage.**
   - Pair each experimental genotype with its controls.
   - Note there are **no** `w1118 x 51375`, `x 51376`, `x 8146`, `x 8147` or `w1118 x Alrm` controls; only driver-side ones (`w1118 x elav`, `w1118 x VT009792`, `w1118 x 95240`, `w1118 x ddc`, `w1118 x repo`).
7. **Later, when porting analysis functions from DrosoClimb:** genotype names contain spaces and `_D10`, so split column names **from the back**:
   - genotype: `split(" ")[0]` → `rsplit(" ", 1)[0]`
     (speedcalc, fallso, pausing, boutdisplacement, boutheight, pauseheight, boutspeed)
   - fly number: `split("_")[1]` → `split("_")[-1]`
     (boutdisplacement, boutheight, pauseheight, boutspeed, distpersec, sectioneddispchunks, positional_arguments)
   - pausenumber: `split("_")[0/1/2]` → behaviour `[-2]`, state `[-1]`, the rest is the genotype
   - deltaversion* functions: `split(" ")[1]` (WT/Expt) → `split(" ")[-1]`
     ("First phase Expt" would otherwise return "phase")
   - `filter(regex="Y.*")` / `"X_.*"` are safe as long as no genotype name contains a capital X or Y.
8. **Functions that need rewriting, not just renaming** — these average *across flies on the same row*, so they depend on the 150-row grid:
   `meangraph` (433), `calcgraph` (396), `fallcalc` (433), `distpersec` (597, uses `iloc[::5]`), `sectioneddispchunks` (620, matches exact `Seconds` values).
   These are per-fly and port cleanly: `speedcalc`, `fallso`, `pausing`, `boutdisplacement`, `boutheight`, `pauseheight`, `boutspeed`, `pausenumber`, `maxvelocity`, `totalheight`.
   `speedcalc` and the `Acc` line divide by a hardcoded `1/fps` — switch to `RealSeconds.diff()`.

---

## Done elsewhere on 2026-09-15 (for reference)
- DrosoClimb: the default branch was renamed back to `main`, the local folder `deltaG_screen` was renamed to `DrosoClimb`, and Correlation-heatmap was deleted.
- `jonnysmagic` was renamed to `timegroup` in DrosoClimb main, Dev and Dev_AsOPN3, and CLOSAR main. Dev_YM and PCA were not touched.
  - **All committed and pushed** — verified 2026-09-16: main, Dev, Dev_AsOPN3 and CLOSAR/main are all 0 ahead / 0 behind origin.
- A GitHub Desktop stash conflict on DrosoClimb main was fixed. The old 2024-11-20 stash is kept as `stash@{0}: backup: old 2024-11-20 main stash`.
