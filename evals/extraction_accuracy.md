# Extraction Accuracy Eval

**Status:** 📋 Spec only (v0.1). No harness yet.

When you change the methodology prompt or upgrade the model (e.g. Sonnet 4.6 → Opus 4.7), you need to know whether extraction quality changed. The [transcript_completeness.md](./transcript_completeness.md) catches broken inputs at capture time. This eval catches drift in the LLM's *interpretation* of good inputs — silent regressions where the LLM starts missing mentions, mis-attributing speakers, or scoring conviction differently.

The plan is a hand-labeled gold subset, three metrics, and a `evals/run.py` harness that reports pass/fail against a frozen reference run.

## What we measure

Three metrics, in order of importance:

### 1. Mention recall (most important)

Given a transcript, did the LLM extract every target-creator trade idea mention? Recall matters more than precision here: the methodology is designed to be exhaustive (Step 1's instruction is "be exhaustive: capture every potential trade-relevant mention"), and the audit step is supposed to catch over-extraction. Missing a mention is silent; over-extracting is loud.

- **Gold set:** every trade-relevant mention from one full episode, hand-labeled with `(timestamp, ticker_or_asset, direction)` triples. Aim for ~30–50 mentions per episode for the Chris Camillo reference.
- **Match rule:** a gold mention is recalled if the extraction has a row within ±10 seconds of the gold timestamp **and** the same ticker (after both sides are normalized via the creator config's naming hints).
- **Target:** ≥0.90 recall on the reference dataset for the production model.

### 2. Speaker attribution accuracy

For each gold mention, did the LLM correctly attribute it to the target creator vs. another host? This is the single most error-prone step in the pipeline (see the `## Speaker Attribution Risks` section of the [audit_report.md](./../examples/chris-camillo-mar-apr-2026/outputs/audit_report.md) — there are 6 risk segments flagged in just 3 episodes).

- **Gold set:** for each mention, `(timestamp, true_speaker)` where `true_speaker ∈ {target, other_host, ambiguous}`.
- **Match rule:** count two confusion-matrix cells specifically:
  - **False positive (worst):** LLM attributed to target, gold says `other_host`. This pollutes the master CSV with another host's positions. Target: ≤2% of gold mentions.
  - **False negative:** LLM said "speaker_confidence: Low" or excluded, gold says `target`. Less harmful — costs recall but doesn't add noise. Target: ≤5%.
- For `ambiguous` golds, accept either Low-confidence target or excluded as correct.

### 3. Conviction score agreement

For each correctly-extracted, correctly-attributed mention, is `conviction_score_0_to_5` within ±1 of human judgment?

- **Gold set:** `(timestamp, ticker, gold_conviction)` with conviction 0–5 per the [trade-idea-extraction.md](./../prompts/trade-idea-extraction.md).
- **Match rule:** `|llm_score − gold_score| ≤ 1`. Conviction is rubric-based but inherently subjective (when does "I'm long" become "I have a massive position"?), so ±1 is the realistic agreement bar.
- **Target:** ≥0.85 of correctly-extracted mentions within ±1.

We do not eval excitement or urgency scores in v0.2 — they are even more subjective than conviction and the rubric needs more episodes of calibration before we can label them confidently.

## What we do NOT measure (and why)

- **Prose quality of synthesis files** (`summary_dashboard.md`, `highest_conviction_ideas.md`, `ticker_timeline.md`). These are derivative — if the master CSV is right, the synthesis files will be right. If the synthesis prose drifts, that's a writing-style change, not a correctness regression.
- **Audit report completeness.** The audit step is itself an LLM judgment call. Auditing the audit is a regress; eval the inputs to audit (the master CSV) instead.
- **Bull/bear thesis quality.** Free-text fields. Comparing them against a gold thesis is just measuring paraphrase agreement, which has its own problems and isn't what we care about.
- **JSON validity of ****`all_mentions_raw.json`****.** That's a parser test, not an eval. Add it as a test in CI separately if it ever fails.

## Building the gold set (v0.2)

The reference Chris Camillo dataset will be the v0.2 gold set. Process:

1. Pick **one** episode as the gold episode. Recommended: `youtube_transcript_he_sold_everything_heres_what_hes_buying_2026-04-24.md` — the longest of the three (1:11:32) and the one with the most speaker-attribution complexity (Jordan's VEEV pick, Dave's Robin Hood Ventures Index).
2. Have a human (Pierre or another analyst) read the transcript and produce `evals/gold/chris-camillo-2026-04-24.csv` with columns:
```
   timestamp,ticker_or_asset,true_speaker,gold_conviction,gold_direction,notes
```
   Aim for the same exhaustiveness bar as Step 1 — capture every mention, not just the headline ones.
3. Cross-check against the existing reference output's `chris_trade_ideas_master.csv` — disagreements are either gold-set errors (fix them) or LLM errors (note them). Either way you learn something.
4. Freeze the gold set with a version number. When you add or relabel rows, bump the version. Eval results are only comparable within a single gold-set version.

The reason we need a hand-labeled gold and can't just diff against the existing reference output: the existing output WAS produced by an LLM. Diffing one LLM run against another tells you about run-to-run variance, not about correctness.

## Running the eval (v0.3, planned)

The future `evals/run.py` will:

```bash
python evals/run.py \
  --gold evals/gold/chris-camillo-2026-04-24.csv \
  --transcript examples/chris-camillo-mar-apr-2026/transcripts/youtube_transcript_he_sold_everything_heres_what_hes_buying_2026-04-24.md \
  --creator prompts/creators/chris-camillo.md \
  --model claude-sonnet-4-6
```

And produce:

```
Mention recall:        46/50  (0.92)  ✅  ≥0.90
Speaker FP rate:       1/50   (0.02)  ✅  ≤0.02
Speaker FN rate:       2/50   (0.04)  ✅  ≤0.05
Conviction within ±1:  41/45  (0.91)  ✅  ≥0.85
PASS
```

Plus a per-mention diff table for human review of the misses.

To make this fast and cheap during prompt iteration, the harness should run **only Steps 0–3** of the methodology (load context, raw extraction, normalization, scoring) — the audit and synthesis steps don't affect any of the three metrics, and skipping them halves the cost.

## Roadmap

- **v0.2** — Hand-label one episode of the reference dataset → first gold CSV. Document the labeling process so others can extend it.
- **v0.3** — `evals/run.py` harness that runs Steps 0–3 against the gold transcript and computes the three metrics. Initially manual; outputs go to `evals/results/{date}-{model}-{prompt-hash}.json`.
- **v0.4** — CI integration. Any change to `prompts/trade-idea-extraction.md` or the model default in `extract.py` triggers the eval and blocks merge if any metric regresses below its target.
- **Stretch** — Hand-label a second creator's gold set (Bill Ackman? Druckenmiller?) so we can detect creator-specific over-fitting in prompt changes.

## Caveats and known limits

- **Small sample.** One episode of one creator means we'll be sensitive to that creator's idiosyncrasies (Chris's explicit position-size language is unusually clear; other investors are subtler). Cross-creator generalization is unverified until v0.5.
- **Rubric subjectivity.** Conviction 4 vs 5 is a judgment call even with the rubric. Two human labelers will disagree on 10–15% of high-conviction rows. The ±1 bar accounts for this; treat any tighter agreement target as suspect.
- **Run-to-run variance is not regression.** Two consecutive runs of the same prompt against the same transcript will produce slightly different CSVs (mention boundaries, summary phrasing). The eval should run N=3 and report the mean, not panic on a single 0.88 recall result.
- **The gold set ages.** When the methodology prompt changes substantively (new column, new rubric), some gold labels become stale. Don't pretend otherwise — re-label the affected rows when the rubric moves.
