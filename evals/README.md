# Evals

Two eval surfaces, with different purposes:

| Eval | Where it runs | What it catches | Status |
|---|---|---|---|
| [Transcript completeness](transcript_completeness.md) | Inside the youtube-transcript skill, at capture time | Truncated/missing transcripts before they reach the LLM | ✅ Live in skill |
| [Extraction accuracy](extraction_accuracy.md) | Standalone harness, after extraction | Drift in LLM extraction quality across prompt or model changes | 📋 Spec only (v0.1) |

## Why both?

**Run-time skill checks** are course-correction. If a YouTube transcript is truncated at the 30-minute mark, the skill notices, scrolls, and re-fetches. By the time the `.md` file is written to disk, it has passed 5 mandatory checks. The methodology never sees broken inputs.

**Formal evals** are regression testing. When you change the methodology prompt or upgrade the model (Sonnet 4.6 → Opus 4.7), you want to know: did anything degrade? Did the LLM start mis-attributing speakers? Did conviction scoring drift? You need a fixed gold set to measure against.

The two are complementary. Lose the in-skill checks and you ship broken inputs. Lose the formal evals and you ship silent regressions.

## v0.1 status

- Transcript completeness: **live in the skill** (5 mandatory checks at the end of every transcript capture). Documented in [`transcript_completeness.md`](transcript_completeness.md) as the spec.
- Extraction accuracy: **spec only** (no harness yet). The reference Chris Camillo dataset in `examples/` will be the basis for the first gold set.

## Roadmap

- v0.2: Hand-label ~30 mentions from one episode of the reference dataset → first extraction-accuracy gold set
- v0.3: `evals/run.py` harness that runs `extract.py` against the reference dataset and computes precision/recall vs the gold set
- v0.4: CI integration so any prompt/model change runs the full eval automatically
