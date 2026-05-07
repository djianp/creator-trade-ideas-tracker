# creator-trade-ideas-tracker

A reproducible methodology for systematically extracting trade ideas from any public investor's YouTube podcast — transcripts to structured CSV/JSON in one command.

> **What this is:** an opinionated extraction framework + reference Chris Camillo dataset.
> **What this isn't:** investment advice, a stock-picking service, or a substitute for doing your own research.

---

## Why this exists

Public investors like [Chris Camillo](https://www.youtube.com/@DumbMoneyLive), Bill Ackman, Stanley Druckenmiller, and dozens of podcast guests share dozens of trade ideas every month — most of them buried in 60+ minute YouTube livestreams without speaker labels, without timestamps for individual ideas, and without any structured record of "who's still long what."

Manually tracking even one investor across a few episodes is hours of work. Tracking conviction *changes* — when did "I have a massive position" become "I exited part of my position" — is essentially impossible without notes.

This project automates the extraction. Run it on a folder of YouTube transcripts, get back:

- A **master CSV** with one row per trade idea mention, scored on conviction (0-5), excitement (0-5), urgency (0-5), direction, position status, time horizon, and trade category
- A **ticker timeline** showing how each position evolved across episodes
- A **highest-conviction ranking** with explicit-quote evidence for every claim
- An **audit report** flagging speaker-attribution risks and unresolved uncertainties
- An **evidence traceability** file mapping every insight back to a verbatim transcript quote with timestamp

All outputs cite verbatim transcript quotes with timestamps, so you can verify any claim in 10 seconds.

---

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/djianp/creator-trade-ideas-tracker
cd creator-trade-ideas-tracker
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Capture transcripts

Two options:

**A. Use the included **[SKILL.md](./skills/youtube-transcript/SKILL.md) (Cowork or Claude Code with browser MCP). Paste a YouTube URL, the skill writes a clean timestamped `.md` with built-in completeness checks.

**B. Bring your own transcripts.** Any `.md` file with metadata header + bracketed `[m:ss]` timestamps works. See [`examples/chris-camillo-mar-apr-2026/transcripts/`](examples/chris-camillo-mar-apr-2026/transcripts/) for the expected format.

### 3. Run the extraction

```bash
python extract.py \
  --transcripts examples/chris-camillo-mar-apr-2026/transcripts/ \
  --creator prompts/creators/chris-camillo.md \
  --output examples/chris-camillo-mar-apr-2026/outputs/
```

Roughly 5 minutes and ~$1-2 of Claude API spend per creator run (3-5 transcripts, ~50k input tokens cached).

### 4. Read the outputs

Start with `summary_dashboard.md` for the top-line view, then dive into `ticker_timeline.md` to see how each position evolved.

---

## Reference example: Chris Camillo, Mar-Apr 2026

The repo ships with a fully-worked example: 3 Dumb Money Live livestreams (Mar 12, Mar 23, Apr 24, 2026) extracted into 11 structured output files. This is what the methodology produces and what your runs will look like.

The single highest-value output is **[`highest_conviction_ideas.md`](./examples/chris-camillo-mar-apr-2026/outputs/highest_conviction_ideas.md)**:

- **Top 10 trade ideas, ranked by a composite score** combining explicit position-size language ("massive", "all in", "tripling down"), repeat mentions across episodes, emotional intensity, thesis specificity, and whether the view survived the audit pass.
- **Every claim has receipts.** For each idea, a timestamped evidence table — quotes copied verbatim from the source transcript, auditable in 10 seconds. AMZN at #1 with 8 supporting quotes including "I'm all in. I'm all in." (Apr 24, [53:21]); SKM at #2 with the explicit "I have a massive SKM position. I don't anticipate selling it until we get close to or beyond the Anthropic IPO" (Mar 23, [53:49]).
- **The caveats that don't show up in a one-line summary.** Leverage / decay risk on heavily-optioned positions, ticker-mapping uncertainty (was "Raku" really Rigaku?), speaker-attribution flags carried over from the audit step.
- **The point:** instead of skimming 3+ hours of livestream looking for what Chris is *actually* most convicted on right now, you open one file and see a defensible starting research list with the receipts attached.

### Other output files worth knowing about

- **[`summary_dashboard.md`](./examples/chris-camillo-mar-apr-2026/outputs/summary_dashboard.md)** — the top-line view. Overall stats, top 10, repeat tickers with conviction trend, current apparent portfolio, watchlist, avoid list, major themes. Open this first.
- **[`ticker_timeline.md`](./examples/chris-camillo-mar-apr-2026/outputs/ticker_timeline.md)** — one section per ticker showing how each position evolved across episodes (date, conviction, what changed). The single best file for spotting "previously massive position → now trimmed" without re-reading every transcript.
- **[`chris_trade_ideas_master.csv`](./examples/chris-camillo-mar-apr-2026/outputs/chris_trade_ideas_master.csv)** — one row per mention (48 rows, 27 columns). The pivot-able structured source of truth that every Markdown file is derived from. Open in a spreadsheet to filter by conviction, direction, or speaker confidence.
- **[`audit_report.md`](./examples/chris-camillo-mar-apr-2026/outputs/audit_report.md)** — the corrections, remaining uncertainties, and speaker-attribution risks the LLM flagged after self-reviewing its own extraction, plus an overall confidence rating for the dataset. The file that tells you how much to trust the rest.
- **[`evidence_traceability.md`](./examples/chris-camillo-mar-apr-2026/outputs/evidence_traceability.md)** — every important insight mapped to its exact source quote, episode, and timestamp. Built so a skeptical reader can verify any claim in the dashboard or ranking without trusting the LLM.

See [`examples/chris-camillo-mar-apr-2026/`](examples/chris-camillo-mar-apr-2026/) for the full set of transcripts and outputs, plus the README in that folder for context on how the run was produced.

---

## How the methodology works

A 6-step workflow that runs as 6 separate Claude API calls, each with the methodology prompt + transcripts cached:

1. **Step 0 — Load context.** Inspect the transcripts, document format, speaker risks, date range. Output: `analysis_context.md`.
2. **Step 1 — Mechanical extraction.** Capture every potential trade-relevant mention exhaustively. Output: `raw_evidence_extraction.csv`.
3. **Step 2 — Speaker attribution + ticker normalization.** Decide who's speaking, normalize tickers (TSMI→TSM, "air sports"→AS), preserve uncertainty. Output: `normalized_mentions.csv`.
4. **Step 3 — Scoring.** Conviction, excitement, urgency, direction, position status, time horizon. Output: `chris_trade_ideas_master.csv`.
5. **Step 4 — Audit.** Verify quotes against source, flag speaker-attribution risks, identify contradictions across episodes. Output: `audit_report.md`.
6. **Step 5 — Synthesis.** Build the per-episode summary, ticker timeline, highest-conviction ranking, JSON dump, dashboard, and traceability file. Output: 6 markdown/JSON files.

Why staged calls instead of one big call: total output exceeds single-response token limits, staging lets you fail fast on bad early-step output, and prompt caching makes it cheap (~75% discount on cached inputs reused across steps).

Full details in [methodology.md](./docs/methodology.md).

---

## Adapting to other creators

The methodology is creator-agnostic. To track a different investor:

1. Create a new file at `prompts/creators/your-creator-name.md` (copy `chris-camillo.md` as a template). Specify: who you're tracking, who else is on the show (so they aren't mis-attributed), known portfolio context, ticker hints for their typical trades.
2. Capture transcripts of their content (skill or otherwise).
3. Run `extract.py --creator prompts/creators/your-creator-name.md ...`.

See [adapting-to-other-creators.md](./docs/adapting-to-other-creators.md) for the full playbook.

---

## Evals

Two eval surfaces:

- **Transcript completeness** ([transcript_completeness.md](./evals/transcript_completeness.md)) — the 5 mandatory checks lifted from the youtube-transcript skill (first/last timestamp, natural ending, segment density, character density). These run *inside* the skill at capture time so a bad transcript never reaches the LLM, and are documented here as the spec.
- **Extraction accuracy** ([extraction_accuracy.md](./evals/extraction_accuracy.md)) — hand-labeled gold subset for measuring whether the LLM extracts every relevant trade idea, attributes speakers correctly, and assigns conviction scores within ±1 of human judgment.

Run-time skill checks catch broken inputs immediately. Formal evals catch regressions when you change the methodology prompt or the model.

---

## Important notes on use

- **Not investment advice.** This tool extracts what a public investor said on a public podcast. It does not endorse following their trades, and the analysis is not a recommendation.
- **Attribution matters.** Every claim links back to the original episode URL and timestamp. Don't strip these. The whole value is verifiability.
- **The methodology is the product, not the creator.** Chris Camillo is the example dataset because his content is exceptionally trade-rich; the same framework works for any public investor's podcast.
- **Don't paywall this.** Selling someone else's words back to your audience without compensating them is gross and probably actionable. Open source, free to use, with prominent source links.

---

## License

MIT. See [LICENSE](LICENSE).

---

## Status

v0.1 — reference example works end-to-end with the included Chris Camillo dataset. The pipeline (`extract.py`) is functional but lightly tested; expect rough edges on transcripts that don't match the expected metadata format. Issues + PRs welcome.
