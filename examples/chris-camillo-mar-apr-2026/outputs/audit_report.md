# Audit Report

## Files Audited
- `youtube_transcript_1_on_amazon_and_almost_no_one_owns_the_stock_2026-03-12.md` — Mar 12, 2026
- `youtube_transcript_end_of_war_trades_2026-03-23.md` — Mar 23, 2026
- `youtube_transcript_he_sold_everything_heres_what_hes_buying_2026-04-24.md` — Apr 24, 2026

## Checks Performed
1. Verified that quoted passages appear verbatim in the source transcript (no paraphrasing in quote fields).
2. Confirmed timestamps align with where quotes appear in the source.
3. Checked speaker attribution: Chris vs. Dave/Jordan, especially in fast back-and-forth exchanges.
4. Re-scanned for missed quick position updates (still long / haven't sold / have no position / staying away).
5. Cross-checked tickers across episodes for consistency (e.g., AMZN, BE, HOOD, TAC, SKM, AS appear in all 3).
6. Stress-tested conviction scores against explicit position-size language and emotional intensity.
7. Confirmed jokes/banter/off-topic conversation (T-Rex in atrium, Pokemon manga as cards, Mr. Beast trip, Margarita lunch, Ghana school children) were excluded from trade-idea extraction unless they had investable substance (e.g., pre-1999 Japanese manga was kept; T-Rex bone was excluded).
8. Verified that ETF tickers (COPX, JETS, UAE, UPRO) match Chris's transcript wording.
9. Confirmed that Dave's and Jordan's positions (Jordan's VEEV, Dave's Robin Hood Ventures Index, Dave's 12% crypto position) are NOT attributed to Chris.
10. Cross-referenced cross-episode contradictions and conviction changes.

## Corrections Made
| Issue | Original | Corrected | Source File | Timestamp |
|---|---|---|---|---|
| Ticker normalization for "Coherent" | Transcript says "COR" | Preserved transcript wording in quote; normalized to COHR (correct ticker for Coherent Corp) in `ticker_or_asset` with note | youtube_transcript_end_of_war_trades_2026-03-23.md | 1:01:46 |
| Ticker normalization for "Lummentum / LI" | Transcript says "LI" | Preserved transcript wording; normalized to LITE in `ticker_or_asset` with note | youtube_transcript_end_of_war_trades_2026-03-23.md | 1:01:50 |
| "TSMI" vs TSM | Transcript says "TSMI" / "TMSI" | Preserved in quote; normalized to TSM with note. The repeated misspellings appear to be voice-to-text errors, not intentional ticker references. | youtube_transcript_end_of_war_trades_2026-03-23.md | 13:01, 1:01:25 |
| "Air sports" / "Solomon shoes" / "Arcteric" | Transcript spells phonetically | Preserved verbatim in quotes; normalized to AS (Amer Sports) with notes citing Salomon and Arc'teryx as the correctly-spelled brand names | youtube_transcript_1_on_amazon_…_2026-03-12.md | 16:18, 51:37 |
| "Trrenium" / "OAI" | Transcript voice-to-text errors | Preserved in quote; normalized as Trainium / OpenAI in summary fields | youtube_transcript_end_of_war_trades_2026-03-23.md | 21:24 |
| Healthcare statement attribution | Transcript shows "I don't buy healthcare stocks … So, I bought a healthcare stock" | The "So, I bought a healthcare stock" sentence is Jordan, who then names Veeva (VEEV). Chris's view (avoid healthcare while tech hot) is captured separately. VEEV is NOT attributed to Chris. | youtube_transcript_he_sold_everything_…_2026-04-24.md | 1:03:22 — 1:04:48 |
| UPRO retirement allocation | Initially stated as "I keep my entire uh retirement portfolio in a triple leveraged uh ETF" | Captured Chris's clarification 30 seconds later that it's actually 20%, not 100%. Both quotes preserved; final "summary_of_chris_view" reflects the corrected 20%. | youtube_transcript_he_sold_everything_…_2026-04-24.md | 49:18 — 49:43 |

## Remaining Uncertainties
| Issue | Why Uncertain | Impact | Recommended Human Review |
|---|---|---|---|
| Raku ticker mapping | "Raku" is phonetic; description (Japanese healthcare imaging co repurposed for AI chip circuitry inspection) most closely matches Rigaku Holdings (TSE: 268A, IPO'd Oct 2024). But the audio could also be a different Japanese-listed company. | Medium — affects whether the position is trackable in any consolidated portfolio view | Listen to the Apr 24 audio at [56:14] to confirm pronunciation; cross-check with a prior Dumb Money episode where Raku was deep-dived |
| SNDK ownership | Chris says "Did you guys see SanDisk keeps just going crazy?" but does not explicitly state ownership. He places it in the same breath as AMD/Micron (his AI sector basket). | Low-medium — small position size implied at most | Treat as ambiguous; do not include in portfolio summary without stronger evidence |
| NVDA ownership | Chris says "I might lever up in Nvidia, too" — implies an existing position, but he never explicitly says "I own NVDA". | Low — universally assumed AI-trade exposure | Reasonable inference; audit-flagged but kept |
| TSM ownership | Chris's enthusiasm ("you got to love that company") is endorsement, not explicit ownership. He may not personally own TSM. | Low — bullish endorsement is the meaningful signal regardless | Mark as inferred ownership; do not include in current-holdings table |
| LLY current state | "I think like 35% of my portfolio back then was in Eli Liy" — refers to past holding. Current state unclear. | Medium — affects whether LLY counts as a current peptide play | Review next episode (peptide deep-dive) for current allocation update |
| GAIN position size | Chris repeatedly says it's a "fun trade" because the company is small/illiquid, suggesting position size is materially smaller than AMZN/BE/SKM/TAC. | Low — doesn't change conviction directionally | Keep at conviction 4 (not 5) to reflect position-size dilution |
| Coherent / Lumentum positions | Chris teases these as future deep-dive but does not say "I own". | Medium — they could be on his watchlist or in his portfolio | Review the planned future episode for position update |

## Speaker Attribution Risks
| Episode | Timestamp | Mention | Risk | Why |
|---|---|---|---|---|
| 2026-03-12 | 32:14 | "I cleared out a bunch of random positions that I had and just went harder into bloom when the drop hit." | Medium | This is JORDAN speaking, not Chris. The conversational flow ("bloom when the drop hit") is consistent with Jordan, who took advantage of the Bloom drop. Excluded from Chris's BE row but flagged. |
| 2026-03-12 | 51:04 | "I'm certainly I still have my Transalta, too. It's not down as much as I thought, though." | Medium | Sounds like Dave or Jordan acknowledging they also still have TAC. Treated as confirmation of group position, but the row is attributed to Chris's separate "I haven't sold my Trans Alta" statement. |
| 2026-03-23 | 5:50—6:55 | Salik discussion | Medium | Back-and-forth between Chris and Dave around the chart. The bearish "people will leave" thesis is most likely Chris's voice. Speaker confidence Medium. |
| 2026-04-24 | 1:04:00 | "So, I bought a healthcare stock." | High (mis-attribution risk) | This is JORDAN, not Chris. Jordan immediately follows with the VEEV name. VEEV is Jordan's pick, not Chris's. The Apr 24 master CSV explicitly notes this — VEEV does NOT appear as a Chris row. |
| 2026-04-24 | 44:55—47:15 | Robin Hood Ventures Index discussion | Medium | The "I bought it and I'm up 20%" line is DAVE describing his own holding. Chris's response ("I'd like to invest in individual companies as opposed to the fund") is captured but the index is NOT attributed to Chris. |
| 2026-04-24 | 17:50—18:30 | Jordan's "I keep about a decade of cash" | Low | Clearly Jordan; not attributed to Chris. |

## Potential Missed Mentions
The following segments were reviewed but excluded as either jokes, banter, off-topic, or not investment-relevant:
- Mar 12: Tim Hortons / Popeye's chicken sandwich anecdote (historical loss reference, not a current trade)
- Mar 23: Ghana / Mr. Beast philanthropy (charity, not investment)
- Mar 23: Margarita restaurant / dinner banter (off-topic)
- Apr 24: T-Rex / dinosaur bone collecting (joke)
- Apr 24: Brian Johnson / peptide guy reality show (anecdote)
- Apr 24: Tweets about CryptoKitties (joke about Dave)
- Apr 24: School board elections / local politics (Dave's personal aside)

The following segments may merit human review in case I missed nuance:
- Mar 23 [55:48 — 1:00:00] HIMS valuation discussion — captured the "$5.2 billion market cap doesn't seem too out of line" comment; uncertain whether this is bullish/neutral or sets up future position.
- Apr 24 [1:09:00 — end] Peptide reality-show anecdote — Chris references a 57-year-old who looks 37 and asks for "the list" of peptides. Could be foreshadowing a specific peptide trade in the upcoming episode but no investable thesis articulated.

## Confidence in Final Dataset
**Medium-High.**

- High confidence on Chris's core recurring positions: AMZN, BE, HOOD, TAC, SKM, AS, GAIN — all have multiple explicit "I own / I haven't sold / I bought" statements with strong contextual speaker attribution.
- High confidence on explicit avoid statements: TSLA (no position), Real estate, Private AI, SMCI, Salik, INTC (lack of conviction).
- Medium confidence on inferred ownership: NVDA, TSM, MU, AMD (he says he owns them but quick passing mentions; no detailed thesis).
- Lower confidence: Raku ticker mapping, SNDK ownership, COR/LITE position status, current LLY state.

The biggest analytical risk is **lack of speaker labels in the transcripts.** I have mitigated this by:
1. Using direct address ("Chris…", "Dave…", "Jordan…") to anchor identity.
2. Pattern-matching content against Chris's known portfolio (AMZN, BE, HOOD, etc.).
3. Marking ambiguous attributions as Medium/Low confidence in the master CSV.
4. Cross-referencing positions across episodes — when the same trade is discussed by Chris with the same conviction tone in 3 episodes, attribution risk is very low.

A second analyst reviewing the audio (not the transcript) would be the gold-standard verification.
