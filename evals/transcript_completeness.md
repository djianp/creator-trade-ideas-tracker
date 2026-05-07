# Transcript Completeness Eval

The methodology only works if the input transcripts are complete. A truncated transcript silently teaches the LLM that the speaker stopped talking — there is no error, just a quieter and less convicted dataset. This eval is the contract between the [youtube-transcript skill](../skills/youtube-transcript/SKILL.md) and `extract.py`: every transcript fed to extraction must pass these five checks first.

## Where this runs

**At capture time, inside the skill** — Step 5 of [`SKILL.md`](../skills/youtube-transcript/SKILL.md). Before the `.md` file is written to disk, the skill must record the actual values for all five checks in the `## Transcript verification` table at the top of the output. If any check fails, the skill scrolls the transcript panel to force lazy-load and re-runs the extraction. If it still fails after one retry, the file is written but with `**Status:** ⚠️ POTENTIALLY INCOMPLETE` so downstream consumers see the warning before they trust the data.

This is course-correction, not regression testing. There is no separate harness — the checks live in the same JS that reads the transcript out of the browser, so they always run on every capture.

## The five mandatory checks

| # | Check | Pass condition | Common failure mode |
|---|---|---|---|
| 1 | **First timestamp at or near video start** | First timestamp ≤ `[0:30]`, ideally `[0:00]` | Transcript panel was scrolled before extraction; first segments not in DOM |
| 2 | **Last timestamp within ~1–2 min of duration** | `\|duration − last_timestamp\| ≤ 120s` | Lazy-loaded transcript panel never finished loading; YouTube cut off captions early |
| 3 | **Ends with natural conclusion** | Last line is an outro, sign-off, `[music]`, or sentence-final punctuation | Truncation mid-sentence — almost always means more segments exist that weren't loaded |
| 4 | **Segment count reasonable for video type** | Edited/polished: 15–25 segs/min. Live streams & auto-generated: 8–12 segs/min | Way under range = partial transcript. Way over range = duplicated segments (re-run) |
| 5 | **Character count plausible** | ~800–2,500 chars/min depending on speech density | Way under range = silence/music-heavy or partial. Way over = duplicates |

Checks 4 and 5 have wide bands because livestreams and auto-generated captions have very different cadences from edited content. Don't tighten the bands — false positives here force the skill to retry on perfectly-good transcripts.

## What the verification table looks like

Every transcript file the skill writes begins with a verification block. This block IS the eval result — there is no separate report.

```markdown
## Transcript verification

**Status:** ✅ Complete

| Check | Result | Detail |
| --- | --- | --- |
| First timestamp at or near video start | ✅ | `[0:00]` |
| Last timestamp within ~1–2 min of duration | ✅ | `[1:05:56]` vs duration `1:06:04` |
| Ends with natural conclusion (not mid-sentence) | ✅ | Last line: "[music]" after sign-off |
| Segment count reasonable | ✅ | 621 segs / 66.1 min = 9.4/min (auto-gen livestream) |
| Character count plausible | ✅ | 59,619 chars (~902/min) |
```

When `extract.py` loads transcripts, it does not currently re-run the checks — it trusts the verification table. If you bring your own transcripts (option B in the README), include this block manually or be prepared for silent extraction quality issues.

## Failure handling

Inside the skill:

1. **Any check fails on first attempt** → scroll the transcript panel to the bottom in the browser, then re-run the segment-extraction JS. YouTube lazy-loads transcript segments; about 80% of failures are fixed by forcing the panel to load all segments.
2. **Any check still fails after one retry** → write the file anyway, but set `**Status:** ⚠️ POTENTIALLY INCOMPLETE` and add an `**Issue:** ...` line under it explaining which checks failed and why.
3. **Video has no captions at all** (no `Show transcript` button on the page) → stop and tell the user. Do not write a file.

The "write anyway with a warning" path exists because some YouTube live streams genuinely have shaky last-minute captions, and a 95%-complete transcript is more useful than no transcript. Downstream consumers (and the user) can see the warning and decide.

## Why this is a separate doc, not just SKILL.md

Two reasons:

1. **The skill describes _how_ to capture; this doc describes _what counts as captured_.** SKILL.md owns the capture procedure (DOM selectors, JS snippets, browser environment differences). This doc owns the success criteria. They evolve at different rates: capture procedures change every time YouTube updates its DOM; success criteria are stable.
2. **Other capture paths exist.** Users who bring their own transcripts (yt-dlp, third-party tools, manual transcription) need a way to validate them against the same bar. This doc is the spec they should target.

If you change either side, update both. A check that drifts out of sync is worse than no check.

## Status

✅ **Live.** All three reference transcripts in [`examples/chris-camillo-mar-apr-2026/transcripts/`](../examples/chris-camillo-mar-apr-2026/transcripts/) were captured with these checks running and all passed.

## Future work

- **Auto-validate at extraction time.** Have `extract.py` parse the verification table and refuse to run on `⚠️ POTENTIALLY INCOMPLETE` transcripts unless `--allow-incomplete` is passed. Today the script trusts the user.
- **Tighten thresholds with more data.** The 8–25 segs/min range is from observation of ~20 captures. Once we have a larger corpus we can split the bands by content type (livestream vs uploaded vs auto-gen vs human-edited) and reduce false-positive retries.
- **Detect mid-sentence truncation programmatically.** The "ends naturally" check is currently human-judgment ("does the last line read like an ending?"). Could be a heuristic: last line contains `[music]`, `bye`, `thanks for watching`, or terminal punctuation `.!?`.
