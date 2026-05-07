# Adapting to Other Creators

The methodology is creator-agnostic. The bits that need to change to track Bill Ackman or Druckenmiller or any other public investor are isolated in one file: [`prompts/creators/{your-creator}.md`](../prompts/creators/). The methodology prompt at [`prompts/trade-idea-extraction.md`](../prompts/trade-idea-extraction.md) does not change.

This doc walks through how to set up a new creator end-to-end. The reference is [`prompts/creators/chris-camillo.md`](../prompts/creators/chris-camillo.md) — open it side-by-side with this doc.

## The 5-step playbook

### 1. Pick a creator and find their content

The methodology assumes:

- **Long-form audio/video.** Podcasts, YouTube livestreams, conference talks, earnings calls. 30–90 minutes per session is the sweet spot — long enough to surface real position language, short enough that one transcript fits comfortably.
- **Public availability.** YouTube/podcast feeds you can transcribe legally. Substack-paywalled content is out unless you have rights to it.
- **Recurring cadence.** The cross-episode timeline (`ticker_timeline.md`) earns its keep when you have ≥3 sessions over a few months. A one-off interview produces useful per-episode output but no conviction-trend data.
- **Explicit-ish position language.** Creators who say "I own / I'm long / I sold" frequently extract well. Creators who only ever speak in third-person about other people's trades extract poorly — the conviction column will be mostly 3s and the highest-conviction ranking will be noise.

Good fits: Chris Camillo (Dumb Money Live), Stanley Druckenmiller (interviews on his macro positions), Bill Ackman (Pershing Square presentations and Twitter spaces), most equity-focused podcast guests.

Mediocre fits: very macro/policy-focused commentators (no specific tickers), traders who only show charts (no audio narration), people who only do tightly-edited 10-min videos (low signal density).

### 2. Capture transcripts

Use the [youtube-transcript skill](../skills/youtube-transcript/SKILL.md) or any tool that produces `.md` files matching the format in [`examples/chris-camillo-mar-apr-2026/transcripts/`](../examples/chris-camillo-mar-apr-2026/transcripts/):

- Markdown header with `**Channel:**`, `**Upload Date:**`, `**Duration:**`, `**URL:**`, `**Extracted:**`
- A `## Transcript verification` table (the [transcript completeness eval](../evals/transcript_completeness.md) — bring your own values if you didn't use the skill)
- A `## Transcript` section with bracketed `[m:ss]` or `[h:mm:ss]` timestamps before each segment

Aim for ≥3 transcripts before the first run. One episode works for a smoke test, but you need cross-episode data to see whether your creator config is working — the same ticker appearing in 3 episodes with consistent attribution is the strongest signal that your speaker-disambiguation rules are right.

### 3. Write the creator config

Copy `prompts/creators/chris-camillo.md` to `prompts/creators/your-creator.md` and rewrite each section. The structure of the file is the contract — keep the section headings, replace the content.

#### `## Show`
Show name, format, typical duration, transcript quality (auto-generated vs human-edited). Mention transcription quirks here so the LLM expects them. Example for Chris: "Auto-generated captions are common, so transcripts often have phonetic transcription errors — preserve verbatim in quote fields, normalize in ticker fields with a note."

#### `## Other regular hosts/guests (NOT the target creator)`

This is the most important section for speaker attribution. List every other regular voice on the show with:
- Their name
- Their role (host, co-host, recurring guest)
- Their distinctive content patterns (Jordan = conservative, "decade of cash"; Dave = host-y, asks probing questions, owns the Robin Hood Ventures Index)
- Specific positions they own that should NOT be attributed to your target

Then provide explicit attribution rules: "Default to {target} if X. Default to {co-host} if Y." This is the LLM's lookup table when it sees a first-person "I own…" without a name attached.

For a show with strict speaker labels (e.g. "CHRIS: I own AMZN."), this section can be shorter — just list the names so the LLM ignores non-target lines. For a show with no labels (Chris Camillo) this section is critical and worth getting right.

#### `## Known portfolio context`

Tickers and themes the target creator has talked about repeatedly across the time range you're capturing. Two purposes:

1. **Anchor speaker attribution.** When the LLM sees "I'm still long my AMZN options" and AMZN is in your known-positions list, it strengthens the case that the speaker is the target. (Conversely, if the speaker mentions a ticker that's on a *co-host's* known list, that's evidence the speaker isn't your target.)
2. **Anchor ticker normalization.** "Bloom" alone is ambiguous — could be Bloom Energy (BE) or any of three other things. If the creator's known portfolio includes BE, "Bloom in AI/energy context" should normalize to BE.

Be specific:
- Stable: ticker, name, why they own it ("Anthropic IPO proxy"), rough position-size language ("massive position", "20% of liquid portfolio")
- Past positions now exited: still useful so the LLM doesn't classify a *historical* mention as a current holding
- Explicit avoids: same — ticker, why, conditional notes ("TSLA — only conditional on a future Elon presentation that 'stuns me'")

Do NOT try to be exhaustive across a creator's entire career. Only capture what matters for the time window you're extracting. The Chris Camillo example covers Mar–Apr 2026; positions from 2023 are noise.

#### `## Naming hints`

A two-column table mapping transcript wordings → correct ticker/name. Cover:
- Phonetic misspellings the auto-transcriber commonly makes for *this creator's* tickers ("air sports" → AS)
- Voice-to-text ticker errors that recur ("TSMI" → TSM, "OAI" → OpenAI)
- Brand → ticker mapping for tickers the creator references by product name ("Robin Hood" → HOOD, "Salomon shoes" → AS)

This table will grow as you run more transcripts — you'll find new transcription errors and add them. Treat it as living documentation.

#### `## Style and conviction language`

The phrases this *specific creator* uses that map to high conviction. Chris's "massive position" / "all in" / "tripling down" is unusual — most creators are more measured. List the equivalents for your creator and what conviction score they map to.

Also: list the creator's conditional phrases ("if X happens, I'd Y") and negative phrases ("I'm staying away") so the LLM scores them correctly.

#### `## Frequency of episodes`

Optional but useful. Tells the LLM whether 3-week gaps between episodes are normal (Chris) or unusual (a daily podcast).

### 4. Calibrate against one known episode

Before running the full pipeline on a folder of transcripts, sanity-check the creator config against one episode you've personally listened to or read.

```bash
python extract.py \
  --transcripts /tmp/calibration-one-episode/ \
  --creator prompts/creators/your-creator.md \
  --output /tmp/calibration-output/
```

Then read `chris_trade_ideas_master.csv` (it will have your creator's name in the data even though the filename is still `chris_*` — that's [intentional schema stability](methodology.md#why-the-methodology-is-creator-agnostic)) and check:

1. **Did the LLM get every mention you remember?** If not — what kind did it miss? Quick passing mentions ("I still have…")? Negative mentions ("I'm staying away from…")? Conditional setups ("if X, I'd Y")? Adjust the methodology by asking — most likely the creator config's "style and conviction language" section needs more examples of the missed phrasings.
2. **Did it get speaker attribution right?** Spot-check 5 random rows against the transcript. If `speaker_confidence: High` rows are wrong, the "Other regular hosts/guests" rules need work — make them more specific about content patterns and direct-address triggers.
3. **Did ticker normalization work?** Phonetic errors should be normalized in `ticker_or_asset` and preserved in the quote field. If a transcribed "air sports" stayed as "air sports" in `ticker_or_asset`, your naming hints table is missing an entry.
4. **Is conviction scoring sane?** Look at the rows with `conviction_score_0_to_5 = 5` and the rows with `conviction_score_0_to_5 = 1`. Do they actually represent the most-and-least convicted mentions in the episode? If the 5s are too generous (everyone gets a 5), refine the conviction-language section.

This calibration loop usually takes 2–3 iterations to get a creator config that works well. Each iteration is one cheap extraction run (~$0.50) — you don't need a full eval harness for this stage.

### 5. Run on the full transcript folder

Once the creator config is calibrated:

```bash
python extract.py \
  --transcripts /path/to/your-creator-transcripts/ \
  --creator prompts/creators/your-creator.md \
  --output examples/your-creator-{date-range}/outputs/
```

Read the audit report (`audit_report.md`) first. It will tell you which mentions to manually verify before trusting the rest of the dataset. If the report's "Confidence in Final Dataset" line says "Low," investigate before relying on the synthesis files.

## Common gotchas

- **Two co-hosts with similar voices/styles.** If the speaker-attribution rules can't reliably distinguish them, the master CSV will be noisy. Mitigations: capture transcripts with speaker diarization (e.g. via `whisper-diarize` or rev.com instead of YouTube auto-captions), or restrict to episodes where one of them is absent.
- **Creator who flip-flops between episodes.** This is actually a feature, not a bug — `ticker_timeline.md` will surface the flips with timestamps and quotes. But your `summary_dashboard.md` "Current apparent portfolio" section will be unreliable; lean on the timeline instead.
- **Show that mixes investing with non-investing content.** A podcast that does 30 minutes of trade ideas and 30 minutes of culture-war commentary will produce a clean output — the LLM ignores non-investment content. But if the ratio is more like 5%/95%, you're paying full transcript-extraction cost for very little signal. Consider trimming transcripts to the investment-relevant timestamps before running.
- **Creator who never names tickers.** "I bought a basket of large-cap energy names" → no ticker → no extraction. The methodology can capture themes (`asset_type: Theme / basket`) but loses specificity. There's no good fix; this kind of creator is a poor fit.
- **Filename naming.** The output filename `chris_trade_ideas_master.csv` is hard-coded in `extract.py` for backward compatibility with the reference dataset. The actual data inside is your creator's data. You can rename the file after extraction if you want, but the methodology prompts and synthesis steps reference the original filename internally.

## What you do NOT need to change

- The methodology prompt at [`prompts/trade-idea-extraction.md`](../prompts/trade-idea-extraction.md). Leave it alone. If you find yourself wanting to edit it for a creator-specific reason, that reason almost certainly belongs in the creator config instead.
- The CSV column schema. The columns are designed to work for any equity-focused investor. Adding columns is a methodology change that will break the [eval harness](../evals/extraction_accuracy.md) when it exists.
- The 6-step pipeline order. Don't skip Step 0 or Step 4 — they're load-bearing for the quality of the output even though they don't produce headline files.

## When extraction quality is unsatisfying

In rough order of likely cause:

1. **Creator config is too thin.** Most quality issues come from this. Add more naming hints, more "style and conviction language" examples, more specific speaker-attribution rules.
2. **Transcripts are bad.** Auto-generated captions on a low-audio-quality stream will have so many phonetic errors that ticker normalization can't keep up. Capture better transcripts (paid services like rev.com produce ~5x cleaner output than YouTube auto-captions).
3. **The creator is genuinely a poor fit.** See "Common gotchas" above. No amount of prompt tuning fixes a creator who never names tickers.
4. **The methodology prompt has a real bug.** This is rare and should usually wait until you have multiple creators showing the same failure mode before changing the shared prompt.

When in doubt, blame the creator config first.
