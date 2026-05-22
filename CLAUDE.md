# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A reproducible methodology for extracting trade ideas from a public investor's YouTube podcast transcripts into structured CSV/JSON/Markdown. The deliverable is the **methodology prompt + pipeline**, not any one creator's data. Chris Camillo is the shipped reference dataset because his content is unusually trade-rich.

The actual "intelligence" lives in prompts, not Python. `extract.py` is a thin orchestrator; `prompts/trade-idea-extraction.md` (~700 lines) is the brain. Most meaningful changes are edits to that prompt, not to code.

## Commands

```bash
pip install -e .                         # install (also exposes `extract` console script)
export ANTHROPIC_API_KEY=sk-ant-...

# Full run (~5 min, ~$1-2 in API spend for 3-5 transcripts)
python extract.py \
  --transcripts examples/chris-camillo-mar-apr-2026/transcripts/ \
  --creator prompts/creators/chris-camillo.md \
  --output /tmp/some-rerun/

python extract.py ... --dry-run          # print cached-context size, make no API calls
python extract.py ... --start-step 4     # resume a crashed run; reuses existing step 0-3 outputs on disk
python extract.py ... --model claude-sonnet-4-6   # default model; override here
```

There is **no test suite** despite `pytest` being declared as a dev extra — `pip install -e ".[dev]"` installs it but no `test_*.py` files exist yet. Don't claim tests pass; there are none. The `schemas/` directory is currently empty.

## Git conventions

- **Commit author email MUST be `pierre.djian@gmail.com`** with name "Pierre Djian". `djianp@gmail.com` — a tempting guess based on the GitHub handle `djianp` and the local git config — is *not* the verified GitHub email; don't use it for commit authorship.
- **Never run `git config --global`.** Thread the identity into individual commands instead: `git -c user.name="Pierre Djian" -c user.email="pierre.djian@gmail.com" commit -m "..."`. The user has multiple repos with different identities; touching global config has cross-repo blast radius.
- **`main` is the default branch.** Don't force-push to it without explicit user authorization; if a history rewrite is genuinely needed, tag a backup first (`git tag pre-rewrite`) and use `--force-with-lease`, never `--force`.
- Public repo at `github.com/djianp/creator-trade-ideas-tracker`. Use the `gh` CLI for GitHub API calls.
- Commit/push only when the user asks.

## Architecture

### Staged API calls, not one big call

`extract.py` runs **11 sequential Claude API calls** (the `STEPS` list), implementing the 6 conceptual methodology steps — Step 5 synthesis fans out into 6 separate file-generating calls (`step_5a`–`step_5f`). The methodology prompt + creator config + all transcripts are concatenated into a single **system prompt sent with `cache_control: ephemeral`**, so every step after the first pays only the cached-read price (~10%) for that bulk. The per-step user message is just the step instruction plus selected prior-step outputs (`requires_prior`).

This staging is deliberate (see `docs/methodology.md` for the full rationale): the combined output exceeds the ~16k single-response token cap; staging fails fast and cheap on bad early output; and caching makes the redundant context effectively free. Each step writes a checkpoint file, which is what `--start-step` resumes from.

Only Step 1 (mechanical extraction) uses extended thinking — it's the highest-recall step and recall errors there can't be recovered downstream.

### The contract between code and prompt

`extract.py`'s `STEPS` instructions reference methodology steps **by name and number** (e.g. "Perform **Step 1 — Mechanical Evidence Extraction**") and by **exact output filename** (e.g. `raw_evidence_extraction.csv`). The methodology prompt's section headers and the file names it documents must stay in sync with `STEPS`. If you rename a step or output file in one place, update both, or the pipeline silently asks for the wrong thing.

The data flow is a fixed dependency chain: Step 1 raw → Step 2 normalized → Step 3 master CSV (the canonical source of truth) → Step 4 audit → Step 5's six files, which are all **projections of the master CSV + audit corrections**. The master CSV is canonical; JSON and Markdown outputs are derived views, intentionally redundant for different consumers.

### Creator-agnostic by design

`prompts/trade-idea-extraction.md` contains **zero creator-specific facts** — every fact about who's being tracked, co-hosts (to avoid mis-attribution), known positions, and ticker hints lives in `prompts/creators/<name>.md`. To support a new investor you write a new creator config and pass `--creator`; you do **not** edit the methodology prompt. See `docs/adapting-to-other-creators.md`.

**Schema-stability concession:** the master CSV is named `chris_trade_ideas_master.csv` and retains a `summary_of_chris_view` column even for non-Chris runs. Keep the column name as-is across creators — schema stability beats aesthetic naming. (The file name may be renamed per creator, but several `STEPS` instructions hardcode `chris_trade_ideas_master.csv`, so changing it means editing `extract.py` too.)

### Closed vocabularies

`direction`, `position_status`, `time_horizon`, `trade_category`, `evidence_strength`, and `asset_type` use closed value sets defined in the methodology prompt (with `unclear`/`uncertain` catch-alls plus a free-text `notes` column). This keeps outputs pivot-able and cross-episode-comparable. Don't introduce free-text variants of these fields.

## Transcript input format

Transcripts are `.md` files with a metadata header and bracketed `[m:ss]` / `[h:mm:ss]` timestamps. `skills/youtube-transcript/SKILL.md` captures them (Cowork / Claude Code with browser MCP) and runs 5 mandatory completeness checks at capture time so a broken transcript never reaches the LLM. Those same checks are documented as a spec in `evals/transcript_completeness.md`. `evals/extraction_accuracy.md` describes a hand-labeled gold subset for regression testing the prompt — both eval surfaces are currently documentation, not automated runners.

## Conventions specific to this repo

- Every output claim must trace to a verbatim transcript quote with episode + timestamp. Preserve original quote wording even after a ticker is normalized in the structured field (phonetic "errors" are sometimes correct). Don't strip source URLs/timestamps from outputs — verifiability is the whole point.
- The shipped `examples/.../outputs/` are committed reference output. Don't overwrite them with reruns; write reruns to `/tmp-outputs/` or another path (`.gitignore` excludes `/tmp-outputs/` and `*.local.md`).
