"""
extract.py — Run the trade-idea extraction methodology against a folder of transcripts.

Stages 6 Claude API calls (Steps 0-5 of the methodology). The methodology prompt,
creator config, and transcripts are cached as the system prompt so each step pays
only the cached-read price (~10% of normal input cost) for the bulk of input tokens.

Usage:
    python extract.py \\
        --transcripts examples/chris-camillo-mar-apr-2026/transcripts/ \\
        --creator prompts/creators/chris-camillo.md \\
        --output /tmp/chris-camillo-rerun/

Requires: ANTHROPIC_API_KEY environment variable.
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    sys.stderr.write(
        "anthropic SDK not installed. Run: pip install anthropic\n"
    )
    sys.exit(1)


DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_METHODOLOGY = "prompts/trade-idea-extraction.md"
MAX_OUTPUT_TOKENS = 16000


@dataclass
class StepSpec:
    name: str
    output_filename: str
    instruction: str
    requires_prior: list[str]  # filenames whose contents to include in the user message
    extended_thinking: bool = False


STEPS: list[StepSpec] = [
    StepSpec(
        name="step_0_context",
        output_filename="analysis_context.md",
        instruction=(
            "Perform **Step 0 — Load Context Only** from the methodology. "
            "Do NOT extract or rank trade ideas yet. "
            "Output the full contents of `analysis_context.md` as your response, "
            "with no preamble, no code fences, just the raw markdown file body."
        ),
        requires_prior=[],
    ),
    StepSpec(
        name="step_1_raw",
        output_filename="raw_evidence_extraction.csv",
        instruction=(
            "Perform **Step 1 — Mechanical Evidence Extraction** from the methodology. "
            "Be exhaustive: capture every potential trade-relevant mention. "
            "Output the full contents of `raw_evidence_extraction.csv` as your response, "
            "with no preamble, no code fences, just the raw CSV body. "
            "First line MUST be the header row."
        ),
        requires_prior=["analysis_context.md"],
        extended_thinking=True,
    ),
    StepSpec(
        name="step_2_normalize",
        output_filename="normalized_mentions.csv",
        instruction=(
            "Perform **Step 2 — Speaker Attribution and Ticker Normalization** from the methodology, "
            "using the prior step's `raw_evidence_extraction.csv` as input (provided below). "
            "Output the full contents of `normalized_mentions.csv` as your response, "
            "with no preamble, no code fences, just the raw CSV body. "
            "First line MUST be the header row."
        ),
        requires_prior=["raw_evidence_extraction.csv"],
    ),
    StepSpec(
        name="step_3_score",
        output_filename="chris_trade_ideas_master.csv",
        instruction=(
            "Perform **Step 3 — Scoring and Classification** from the methodology, "
            "using the prior step's `normalized_mentions.csv` as input (provided below). "
            "Output the full contents of `chris_trade_ideas_master.csv` as your response, "
            "with no preamble, no code fences, just the raw CSV body. "
            "First line MUST be the header row."
        ),
        requires_prior=["normalized_mentions.csv"],
    ),
    StepSpec(
        name="step_4_audit",
        output_filename="audit_report.md",
        instruction=(
            "Perform **Step 4 — Audit / Stress Test** from the methodology, "
            "using the prior step's `chris_trade_ideas_master.csv` and the original transcripts as input. "
            "Verify quotes against source text. Output the full contents of `audit_report.md` as your response, "
            "with no preamble, no code fences, just the raw markdown body."
        ),
        requires_prior=["chris_trade_ideas_master.csv"],
    ),
    StepSpec(
        name="step_5a_by_episode",
        output_filename="chris_trade_ideas_by_episode.md",
        instruction=(
            "Perform **Step 5 synthesis — File 1: `chris_trade_ideas_by_episode.md`** from the methodology, "
            "using the master CSV and audit report as input. "
            "Output the full file body as your response, no preamble, no code fences."
        ),
        requires_prior=["chris_trade_ideas_master.csv", "audit_report.md"],
    ),
    StepSpec(
        name="step_5b_timeline",
        output_filename="ticker_timeline.md",
        instruction=(
            "Perform **Step 5 synthesis — File 2: `ticker_timeline.md`** from the methodology, "
            "using the master CSV as input. "
            "Output the full file body as your response, no preamble, no code fences."
        ),
        requires_prior=["chris_trade_ideas_master.csv"],
    ),
    StepSpec(
        name="step_5c_highest_conviction",
        output_filename="highest_conviction_ideas.md",
        instruction=(
            "Perform **Step 5 synthesis — File 3: `highest_conviction_ideas.md`** from the methodology, "
            "using the master CSV and audit report as input. "
            "Output the full file body as your response, no preamble, no code fences."
        ),
        requires_prior=["chris_trade_ideas_master.csv", "audit_report.md"],
    ),
    StepSpec(
        name="step_5d_json",
        output_filename="all_mentions_raw.json",
        instruction=(
            "Perform **Step 5 synthesis — File 4: `all_mentions_raw.json`** from the methodology, "
            "using the master CSV as input. "
            "Output a single JSON array (one object per row of the master CSV) as your response, "
            "with no preamble, no code fences, just valid JSON. The first character must be `[` and the last `]`."
        ),
        requires_prior=["chris_trade_ideas_master.csv"],
    ),
    StepSpec(
        name="step_5e_dashboard",
        output_filename="summary_dashboard.md",
        instruction=(
            "Perform **Step 5 synthesis — File 5: `summary_dashboard.md`** from the methodology, "
            "using the master CSV and audit report as input. "
            "Output the full file body as your response, no preamble, no code fences."
        ),
        requires_prior=["chris_trade_ideas_master.csv", "audit_report.md"],
    ),
    StepSpec(
        name="step_5f_traceability",
        output_filename="evidence_traceability.md",
        instruction=(
            "Perform **Step 5 synthesis — File 6: `evidence_traceability.md`** from the methodology, "
            "using the master CSV as input. "
            "Output the full file body as your response, no preamble, no code fences."
        ),
        requires_prior=["chris_trade_ideas_master.csv"],
    ),
]


def load_transcripts(transcripts_dir: Path) -> list[tuple[str, str]]:
    """Return list of (filename, content) for each .md file in the directory."""
    md_files = sorted(transcripts_dir.glob("*.md"))
    if not md_files:
        sys.stderr.write(f"No .md transcripts found in {transcripts_dir}\n")
        sys.exit(1)
    return [(p.name, p.read_text(encoding="utf-8")) for p in md_files]


def build_system_prompt(methodology: str, creator_config: str, transcripts: list[tuple[str, str]]) -> str:
    """Assemble the system prompt: methodology + creator config + all transcripts."""
    transcript_blocks = []
    for name, content in transcripts:
        transcript_blocks.append(f"### Transcript file: `{name}`\n\n{content}\n")

    return (
        "# METHODOLOGY\n\n"
        f"{methodology}\n\n"
        "---\n\n"
        "# CREATOR CONFIG\n\n"
        f"{creator_config}\n\n"
        "---\n\n"
        "# TRANSCRIPTS\n\n"
        f"{chr(10).join(transcript_blocks)}"
    )


def strip_code_fences(text: str) -> str:
    """Strip leading/trailing ```lang ... ``` if the model wrapped output in fences."""
    text = text.strip()
    fence_pattern = re.compile(r"^```[a-zA-Z0-9_]*\n(.*)\n```$", re.DOTALL)
    m = fence_pattern.match(text)
    if m:
        return m.group(1)
    return text


def run_step(
    client: anthropic.Anthropic,
    model: str,
    system_prompt: str,
    step: StepSpec,
    prior_outputs: dict[str, str],
) -> str:
    """Execute one methodology step. Returns the raw text response."""
    user_parts = [step.instruction]

    for fname in step.requires_prior:
        if fname in prior_outputs:
            user_parts.append(f"\n\n---\n\n## Prior step output: `{fname}`\n\n{prior_outputs[fname]}")

    user_message = "\n".join(user_parts)

    kwargs = dict(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    if step.extended_thinking:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": 8000}

    response = client.messages.create(**kwargs)

    text_blocks = [b.text for b in response.content if b.type == "text"]
    return "".join(text_blocks)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract trade ideas from a folder of YouTube transcripts using the methodology pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--transcripts", required=True, type=Path, help="Directory containing .md transcript files")
    parser.add_argument("--creator", required=True, type=Path, help="Path to the creator config .md file")
    parser.add_argument("--output", required=True, type=Path, help="Output directory for generated files")
    parser.add_argument("--methodology", default=DEFAULT_METHODOLOGY, type=Path, help=f"Path to methodology prompt (default: {DEFAULT_METHODOLOGY})")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Anthropic model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--start-step", type=int, default=0, help="Start at this step index (0-10) — useful for retrying after a partial run")
    parser.add_argument("--dry-run", action="store_true", help="Print the cached-context size and exit without making API calls")
    args = parser.parse_args()

    if not args.transcripts.is_dir():
        sys.stderr.write(f"Transcripts directory not found: {args.transcripts}\n")
        return 1
    if not args.creator.is_file():
        sys.stderr.write(f"Creator config not found: {args.creator}\n")
        return 1
    if not args.methodology.is_file():
        sys.stderr.write(f"Methodology prompt not found: {args.methodology}\n")
        return 1

    if "ANTHROPIC_API_KEY" not in os.environ and not args.dry_run:
        sys.stderr.write("ANTHROPIC_API_KEY environment variable not set.\n")
        return 1

    args.output.mkdir(parents=True, exist_ok=True)

    transcripts = load_transcripts(args.transcripts)
    methodology = args.methodology.read_text(encoding="utf-8")
    creator_config = args.creator.read_text(encoding="utf-8")
    system_prompt = build_system_prompt(methodology, creator_config, transcripts)

    print(f"Loaded {len(transcripts)} transcript(s) from {args.transcripts}")
    print(f"System prompt size: {len(system_prompt):,} chars (~{len(system_prompt) // 4:,} tokens)")

    if args.dry_run:
        print("Dry run — exiting before API calls.")
        return 0

    client = anthropic.Anthropic()
    prior_outputs: dict[str, str] = {}

    for i, step in enumerate(STEPS):
        if i < args.start_step:
            existing = args.output / step.output_filename
            if existing.is_file():
                print(f"[skip] Step {i} ({step.name}) — using existing {step.output_filename}")
                prior_outputs[step.output_filename] = existing.read_text(encoding="utf-8")
            else:
                print(f"[warn] Step {i} ({step.name}) — skipped via --start-step but no existing output found")
            continue

        print(f"[step {i}] {step.name} → {step.output_filename}")
        t0 = time.time()
        try:
            raw = run_step(client, args.model, system_prompt, step, prior_outputs)
        except anthropic.APIError as e:
            sys.stderr.write(f"API error in step {i}: {e}\n")
            return 1

        cleaned = strip_code_fences(raw)
        out_path = args.output / step.output_filename
        out_path.write_text(cleaned, encoding="utf-8")
        prior_outputs[step.output_filename] = cleaned

        elapsed = time.time() - t0
        print(f"           wrote {len(cleaned):,} chars in {elapsed:.1f}s")

    print(f"\nDone. Outputs in {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
