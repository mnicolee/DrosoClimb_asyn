# DrosoClimb_asyn — TODO

Last updated: 2026-09-15. Nothing has been built yet. This file records the plan and where we stopped.

---

## Where we stopped (pick up here)

**Open decision: how to turn raw frame times into fixed 0.2 s labels (0.0, 0.2 … 29.8).**

The question as it was left:
> "ok why dont we look for lower than 0.1s bursts as our criteria for burst? secondly, ultimately i DO need to shift them into like fixed integer time scales as per analysis so then it would be like 2.3, 2.5, 2.7 etc so if the burst captures in a way where its larger than 0.1 but lower than 0.15, it might end up as the same 2.4, 2.4 then it would be a conflict, no?"

**Agreed:** a burst is two frames **less than 0.1 s apart**. Keep the **later** frame.

**Still to choose between two methods** (tested on all 91 PD ClimbLogs, 273 phases):

| | Method A: fixed labels from phase start | Method B: follow the gaps |
|---|---|---|
| How | label = nearest 0.2 s counted from the first real camera frame of the phase | each frame goes 1 label after the previous one (2 if the gap is about 0.4 s); gap < 0.1 s = burst |
| Two frames on the same label | bursts 97; **gap 0.10–0.15 s: 10 (8 phases)**; gap ≥ 0.15 s: 50 → 81 phases affected | never (except bursts) |
| Weak point | camera runs at 0.199 s per frame, not 0.200, so frames slide against the labels and clash | labels end **1 slot off** in 44 phases and **2 slots off** in 3, out of 273 (a 0.2–0.4 s shift by the end) |
| If chosen | clash rule: keep the later frame, earlier label becomes NaN if nothing else fills it | — |

Leaning: B fits the rules better (no clashes; only bursts lose a frame). **Not decided.**

### Findings behind this (so they don't need re-checking)
- **Frame timing:** 98.5% of gaps between frames are 0.15–0.25 s. The camera runs at about 0.199 s per frame.
- **Rounding each timestamp to 1dp doesn't work.** Because of that drift, frames cross the .x5 boundary and flip between odd and even tenths, which would mark about 8.6% of rows as NaN. Example: `20260819\elav x 8146_D10\ClimbLog_2026-08-19_15-53-07.csv`, Third phase, where 1.630 → 1.862 flips.
- **4 or 6 frames in one whole second is NOT a camera error.** It's frames landing a few ms either side of the second mark, e.g. 3.989 or 11.999. So don't count frames per whole second; this also affects the old `timegroup` + `head(5)`.
- **A short gap isn't always a burst.** 0.265 then 0.132 s (sum 0.397 = 2 slots) is a late frame followed by an early one, and both frames are real (`20260819\elav x 51375_D10\...15-38-01.csv`, Third phase, rows 66–67).
- **The first row of every phase is an empty "No blobs found" row** logged at phase start. The first real frame comes about 0.13–0.17 s later. Treat row 1 as empty, not as a frame.
- **Short file:** `20260903\elav x 51375_D30\ClimbLog_2026-09-03_18-02-58.csv` has only 137 rows in First phase, with 13 small gaps in 0–19 s. The chosen method must fill those gaps with NaN at the right places.
- **No earlier code anywhere** (DrosoClimb main/Dev/Dev_AsOPN3, CLOSAR, OSARanalysis_NLee) handles bursts or frame gaps.

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
- Written exactly in Nicole's style: no comments, minimal markdown, no try/except.
- Same idioms as DrosoClimb `1. Renamingfiles.ipynb`, `2. Fileprocessing.ipynb` and `NLCLIMB.py` (`labcomp`/`specifiedpath`/`openPath`, `os.listdir` loops, `print("done!")`).
- Plan first, then build only on command. Nicole commits and pushes herself.

---

## Remaining steps (in order)
1. **Decide Method A or B** for fixed time labels (top of this file).
2. Write `1. Renamingfiles.ipynb`, then do a **dry run**: list every copy and folder it would create, and confirm before copying.
3. Run step 1 and check that the file counts match the raw data (91 ClimbLogs).
4. Write `NLCLIMB_asyn.py` (the new `fivefps` equivalent with the chosen method, plus `removenans`, `onlycolsneeded`, `cleanup` adapted to 3 × 150 rows) and `2. Fileprocessing.ipynb`.
5. Run step 3 and check that each output has 450 rows (3 × 150) and sensible NaN counts. Look at the short file (137 rows) specifically.
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

---

## Done elsewhere on 2026-09-15 (for reference)
- DrosoClimb: the default branch was renamed back to `main`, the local folder `deltaG_screen` was renamed to `DrosoClimb`, and Correlation-heatmap was deleted.
- `jonnysmagic` was renamed to `timegroup` in DrosoClimb main, Dev and Dev_AsOPN3, and CLOSAR main. Dev_YM and PCA were not touched.
  - Nicole committed main and Dev_AsOPN3.
  - **Dev and CLOSAR still need committing.**
- A GitHub Desktop stash conflict on DrosoClimb main was fixed. The old 2024-11-20 stash is kept as `stash@{0}: backup: old 2024-11-20 main stash`.
