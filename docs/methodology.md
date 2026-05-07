# Methodology

This document explains *why* the extraction pipeline is shaped the way it is. The full prompt that drives the LLM lives at [`prompts/trade-idea-extraction.md`](../prompts/trade-idea-extraction.md); this is the design rationale.

## The problem

A single Dumb Money Live livestream is ~60–75 minutes, ~60,000 characters, ~15,000 input tokens. Across one episode, Chris Camillo will mention 15–25 distinct trade ideas — sometimes for ten minutes (his AMZN thesis), sometimes for five seconds ("I still haven't sold my Trans Alta"). The five-second mentions are often the most valuable, because they tell you the *current state* of a position whose original thesis was laid out three episodes ago.

A single "summarize the trade ideas in this transcript" call to an LLM gives you back the obvious headline ideas and loses the quick passing mentions. It also tends to:

- Smooth over contradictions ("conviction is high" — but Chris also said he trimmed in the March drawdown)
- Confuse speakers (Jordan's VEEV pick attributed to Chris)
- Hallucinate ticker normalizations ("air sports" silently rewritten as Asia Sports Inc instead of Amer Sports)
- Skip the audit ("did this quote actually appear at this timestamp?") because there's no separate step where it has to

The methodology is designed to defeat each of these failure modes by making them their own step with their own success criterion.

## The 6-step pipeline

Each step is one Claude API call. The methodology prompt + creator config + transcripts are all sent as the **system prompt** with `cache_control: ephemeral`, so steps 1–5 pay only the cached-read price (~10% of normal input cost) for that bulk of context. The per-step user message is just the instruction + the prior step's output.

### Step 0 — Load context

**Output:** `analysis_context.md`

The LLM reads the transcripts but does not extract yet. It records: how many files, what date range, what timestamp format, whether speaker labels exist, what the speaker-attribution risks are, what's known about the creator's recurring positions.

Why a separate step: it forces the LLM to commit to its understanding of the source material in writing before it starts extracting. If Step 0 says "no speaker labels, three speakers, all male, similar speech patterns" and Step 1 then attributes 47/50 mentions to Chris with `speaker_confidence: High`, that mismatch is visible. Without Step 0 the over-confidence is invisible.

It also catches the fast-failure cases: "this folder has 0 transcripts" or "this isn't a Dumb Money Live transcript at all" surface in Step 0 instead of after a $1 extraction run.

### Step 1 — Mechanical evidence extraction

**Output:** `raw_evidence_extraction.csv`

Every potentially-relevant mention. The instruction is "be exhaustive" — the LLM is *encouraged* to over-extract. Quick passing mentions ("I still have my Trans Alta"), ETF mentions, sector themes, future deep-dive teases, "I'm staying away" comments — all in.

Why before any cleanup or scoring: bundling extraction with normalization causes the LLM to drop mentions it can't immediately classify. Asking only "what was said?" lets it capture noise that downstream steps will filter or fix.

Step 1 is the only step that uses `extended_thinking` (`budget_tokens: 8000`). The thinking budget pays off here because exhaustive extraction across a 60-min transcript is the highest-recall step in the pipeline and recall errors here cannot be recovered later. The other steps either transform Step 1's output or audit it — they don't need to scan from scratch.

### Step 2 — Speaker attribution + ticker normalization

**Output:** `normalized_mentions.csv`

For each Step 1 row, decide who's speaking (target creator vs. other host vs. ambiguous) and normalize the ticker (`TSMI` → TSM, `air sports` → AS, `Solomon shoes` → Salomon). Preserve uncertainty: `speaker_confidence` ∈ {High, Medium, Low}; `ticker_or_asset = "uncertain"` is a valid value.

Why separate from Step 1: extraction wants to be permissive, attribution wants to be careful. Doing them together produces a CSV that's both incomplete and overconfident. Splitting them lets each step optimize for its own bar.

The verbatim transcript wording is preserved in the quote field even after the ticker is normalized in the structured field. This matters because phonetic transcription errors aren't always errors — sometimes "air sports" really is Air Sports Inc. Keeping the original quote lets a human re-judge.

### Step 3 — Scoring and classification

**Output:** `chris_trade_ideas_master.csv` (the headline file)

Conviction (0–5), excitement (0–5), urgency (0–5), direction, position status, time horizon, trade category, bull/bear thesis, evidence strength. The full rubric is in [`prompts/trade-idea-extraction.md`](../prompts/trade-idea-extraction.md).

This is the column-heavy file users will actually pivot on. By this point the data has been (a) extracted exhaustively, (b) attributed to the right speaker, (c) normalized for tickers — the LLM only needs to score, not also re-read from the transcript. That reduces score drift across runs.

### Step 4 — Audit

**Output:** `audit_report.md`

Verify quotes against source text. Flag speaker attribution risks. Identify cross-episode contradictions. Note remaining uncertainties. Confidence-rate the final dataset.

Why a separate audit step instead of asking Step 3 to do its own QA: a model checking its own work is a known weak spot. Posing the audit as "review someone else's work" — even though the someone-else is also you — produces noticeably more corrections than self-review. The audit step is also what makes the dataset *defensible*: every flagged risk goes in a table, every correction is visible, and the final "Confidence in Final Dataset" rating tells the user how much to trust the rest.

The audit catches things the earlier steps cannot:

- "I bought a healthcare stock" attributed to Chris but actually said by Jordan (Apr 24, [1:04:00])
- "TSMI" vs TSM ticker normalization needing a note about transcription error
- Conviction 5 on a position the speaker only mentioned once in passing
- "I still have my Bloom" not picked up because it followed an unrelated topic

### Step 5 — Synthesis

**Outputs (six files):**

- `chris_trade_ideas_by_episode.md` — per-episode breakdown
- `ticker_timeline.md` — per-ticker evolution across episodes
- `highest_conviction_ideas.md` — top-10 ranked with caveats
- `all_mentions_raw.json` — structured JSON of every mention
- `summary_dashboard.md` — top-line view, top 10, repeat tickers, watchlist, avoid list
- `evidence_traceability.md` — every claim mapped to source quote with timestamp

These are derivative — they are different views of the same underlying data in `chris_trade_ideas_master.csv` plus the audit corrections from Step 4. The reason to produce them as separate API calls instead of one big one is the [output token limit](#why-staged-calls-instead-of-one-big-call): a single response can only emit ~16k tokens, and the six synthesis files together exceed that.

The redundancy across the six files is intentional. Different consumers want different views: the dashboard for a quick scan, the timeline for tracking one ticker, the by-episode for chronological narrative, the JSON for programmatic use. Forcing the user to derive any of these from the master CSV themselves is friction.

## Why staged calls instead of one big call

Three reasons:

1. **Output token cap.** The full set of outputs (one Step 0 file + four CSVs + seven Markdown files + one JSON) is roughly 200,000 characters / 50,000 tokens. Single-response output limits cap a Claude call at ~16k tokens. Even if you could fit it all in one response, you'd be at the absolute edge of the budget — one extra row of audit findings and the file is truncated mid-quote.
2. **Fail fast on bad early-step output.** If Step 0 reveals the folder has no transcripts, you stop after one cheap call. If Step 1 mis-attributes everyone to Chris, you see it in the raw CSV before paying for Steps 2–5. With a single mega-call, every error is paid for in full.
3. **Prompt caching makes staging effectively free.** The methodology + creator config + transcripts are ~50,000 input tokens. Sent six times with caching, you pay 1× full price + 5× cached-read price (~10% of full). Total input cost ≈ 1.5× the single-call cost, *and* you get fail-fast behavior, *and* you get checkpoint files you can resume from.

The `extract.py` script supports `--start-step N` so a partial run that crashed on Step 4 can be resumed from Step 4 using the existing Steps 0–3 outputs on disk.

## Why CSV + JSON + Markdown for the same data

Different tools want different shapes:

- **CSV** for spreadsheet pivot tables, conviction-trend filtering, and as the one file that other Markdown synthesis steps treat as canonical input
- **JSON** for programmatic consumption (custom dashboards, downstream scripts, anything that needs to round-trip)
- **Markdown** for human reading — the by-episode narrative, the timeline, the highest-conviction ranking, the audit report

The master CSV is the source of truth. JSON and Markdown are projections of it. Generating them as separate steps is wasteful in tokens but cheap thanks to caching, and it produces output that's actually pleasant to read instead of one giant CSV-with-extra-columns that nobody wants to open.

## Allowed-values vocabularies

The methodology defines closed vocabularies for `direction`, `position_status`, `time_horizon`, `trade_category`, `evidence_strength`, and `asset_type`. The full lists are in [`prompts/trade-idea-extraction.md`](../prompts/trade-idea-extraction.md).

Why constrain instead of letting the LLM free-text these fields:

- **Pivot-ability.** "Long" and "long" and "Bullish" and "going long" all mean the same thing in free text but break a `value_counts()`.
- **Cross-episode comparability.** When the same ticker appears in three episodes with three different `position_status` values, you want to be able to tell "owns → considering → would buy if condition met" is a real trajectory, not just paraphrase noise.
- **Easier auditing.** A reviewer can scan a column of seven possible values much faster than seven hundred unique strings.

The cost is occasional awkwardness when a real situation doesn't fit the vocabulary cleanly. The methodology handles this with the catch-all `unclear` value plus a free-text `notes` column where the LLM can explain.

## Where the methodology is weakest

Honest assessment of the failure modes the methodology does not handle well:

- **Multi-host shows without speaker labels.** The Chris Camillo dataset has three speakers and no labels in the auto-generated YouTube captions. The audit report flags 6 attribution risks across 3 episodes. For a show with five speakers and overlapping speech (e.g. CNBC), this approach degrades fast. Mitigations: add explicit speaker turn detection in the transcript, or capture audio with diarization.
- **Investors who don't use explicit position language.** Chris's "massive position" / "all in" / "tripling down" makes conviction scoring tractable. An investor who only ever says "I like X" and "I don't like Y" gives the rubric much less to grip. The conviction column will collapse to mostly 3s and 2s, making the highest-conviction ranking less informative.
- **Single-episode runs.** The methodology pays off when you have ≥3 episodes — the cross-episode timeline and conviction-change detection are where the structured data earns its keep. On a single episode, you're paying for staged extraction without getting the comparison benefit.
- **Off-the-cuff hot takes.** A passing "I bought some X yesterday" with no thesis or context will be captured (Step 1) and scored as a real trade idea (Step 3). Whether that's correct depends on what the user wants — for a "what is the creator currently long" view, yes. For a "what does the creator think the best ideas are" view, the noise is unhelpful. The `evidence_strength` column ('explicit' / 'inferred' / 'weak / ambiguous') is the workaround.
- **Sarcasm and exaggeration.** The methodology has explicit handling ("If a statement might be sarcasm or exaggeration, capture it only if potentially relevant and mark `evidence_strength = weak / ambiguous`"), but the LLM is not great at detecting it. Quotes that read literally as "I'm putting everything at risk" might be hyperbole; the methodology has no good way to distinguish.

## Why the methodology is creator-agnostic

Nothing in `prompts/trade-idea-extraction.md` references Chris specifically — every Chris-specific fact lives in `prompts/creators/chris-camillo.md`. To track a different investor, you write a new creator config; the methodology prompt does not change. See [adapting-to-other-creators.md](adapting-to-other-creators.md) for the full playbook.

The one creator-specific naming concession is that the master CSV is called `chris_trade_ideas_master.csv` and the column `summary_of_chris_view` retains the Chris name, both for backward compatibility with the reference dataset. New creator runs can rename the file but should keep the column name as-is — schema stability matters more than aesthetic naming.
