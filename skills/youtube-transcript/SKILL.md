---
name: youtube-transcript
description: Extract the complete timestamped transcript from a YouTube video and save it to a clean markdown file ready for downstream LLM processing (summarization, analysis, search). Use this skill whenever the user wants to get, pull, save, or extract a transcript or captions from a YouTube video, prepare a video for later analysis in Claude / Cowork / Claude Code, or convert a YouTube URL into reusable text. Trigger on any YouTube URL paired with words like "transcript", "captions", "extract", "save", "pull", "get the text", or "convert to markdown" — and even when the user just pastes a YouTube URL and asks for "the text" or "the words" of the video.
argument-hint: <YouTube URL>
---

# YouTube Transcript Extractor

Extract the full timestamped transcript from a YouTube video and save it as a clean markdown file. The output is optimized for downstream LLM processing — no analysis, no summary, no fluff. Just the raw transcript with light metadata and (when available) chapter markers, ready to feed into Claude AI, Cowork, or Claude Code.

## When to use this skill

- "Extract the transcript from this YouTube video"
- "Save the captions of this video to a file"
- "Pull the text from this YouTube link"
- "Get me the transcript of [URL] so I can analyze it later"
- The user pastes a YouTube URL and says "transcript", "captions", or "the words"

## Arguments

`$ARGUMENTS` should be a YouTube video URL. If the user provides a URL inline in their message, use that directly.

## Environment-specific delivery

The `javascript_tool` in Claude in Chrome **truncates output at ~1000 chars**. The full transcript can never be read back through it directly. The workaround differs by environment — see Step 6.

**In Cowork or Claude Code:** Use the console.log chunking approach (Step 6A) to pull the transcript into context, then write a `.md` file directly to disk. Clean and reliable.

**In Claude.ai:** Assemble the file in JavaScript and trigger a browser download as `.txt` (Step 6B). Chrome on Mac silently blocks `.md` blob downloads, so `.txt` is required. The content inside is valid markdown and can be renamed to `.md` at any time.

**MCP timeout recovery:** If the MCP server times out mid-task, tell the user to restart Claude Desktop. The `window._transcript` and `window._chapters` variables survive in the browser tab — simply reconnect and resume from Step 5.

## Process

### Step 1: Navigate and capture metadata

```
Use tabs_context_mcp with createIfEmpty: true
Navigate to the YouTube URL (reuse an existing tab in the MCP group, or create a new one)
Wait ~3 seconds, take a screenshot to confirm the page loaded
```

While on the page, note:
- **Video title** — from the `h1` or page title
- **Channel name** — from the channel link below the video
- **Upload date** — from the metadata block
- **Video duration** — from the player (e.g. `1:06:04`)

### Step 2: Expand description and extract chapters

Click the **"...more"** button in the video description to expand it. Then run this JS to detect and extract any chapter / key moments list:

```javascript
// Extract chapter markers from the expanded description
var descEl = document.querySelector('#description-inline-expander')
  || document.querySelector('ytd-text-inline-expander');
var descText = descEl ? descEl.innerText : '';

var chapterMatches = [];
// Matches [MM:SS] or [H:MM:SS] followed by a chapter title on the same line
var chapterRegex = /\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*([^\n\[]+)/g;
var match;
while ((match = chapterRegex.exec(descText)) !== null) {
  var title = match[2].trim().replace(/\s+/g, ' ');
  if (title.length > 0) chapterMatches.push('[' + match[1] + '] ' + title);
}
window._chapters = chapterMatches.length > 0 ? chapterMatches.join('\n') : null;
JSON.stringify({
  chapterCount: chapterMatches.length,
  first: chapterMatches[0] || null,
  last: chapterMatches[chapterMatches.length - 1] || null
});
```

- If `chapterCount > 0`: a **Chapters / Key Moments** section will be included in the output file.
- If `chapterCount === 0`: omit the section entirely — do not add a placeholder.

### Step 3: Open the transcript panel

Scroll down in the expanded description to find the **"Show transcript"** button and click it. The transcript panel opens on the right side of the page.

If no "Show transcript" button is visible: the video has no captions — stop and tell the user.

### Step 4: Extract the full transcript

```javascript
// Step 4a: Extract all segments — handles both old and new YouTube architectures
var entries = [];

// Architecture 1 (new): transcript-segment-view-model
var newSegs = document.querySelectorAll('transcript-segment-view-model');
if (newSegs.length > 0) {
  for (var i = 0; i < newSegs.length; i++) {
    var tsEl  = newSegs[i].querySelector('.ytwTranscriptSegmentViewModelTimestamp');
    var txtEl = newSegs[i].querySelector('[role="text"]') || newSegs[i].querySelector('.ytAttributedStringHost');
    if (tsEl && txtEl) {
      entries.push("[" + tsEl.textContent.trim() + "] " + txtEl.textContent.trim());
    }
  }
}

// Architecture 2 (old): ytd-transcript-segment-renderer
if (entries.length === 0) {
  var oldSegs = document.querySelectorAll('ytd-transcript-segment-renderer');
  for (var i = 0; i < oldSegs.length; i++) {
    var tsEl  = oldSegs[i].querySelector('.segment-timestamp');
    var txtEl = oldSegs[i].querySelector('.segment-text');
    if (tsEl && txtEl) {
      entries.push("[" + tsEl.textContent.trim() + "] " + txtEl.textContent.trim());
    }
  }
}

window._transcript = entries.join("\n");
window._transcriptSegmentCount = entries.length;
window._transcriptCharCount = window._transcript.length;

JSON.stringify({
  architecture: newSegs.length > 0 ? 'new (transcript-segment-view-model)' : 'old (ytd-transcript-segment-renderer)',
  segmentCount: window._transcriptSegmentCount,
  charCount: window._transcriptCharCount,
  firstTimestamp: entries[0] ? entries[0].substring(0, 12) : null,
  lastTimestamp: entries[entries.length - 1] ? entries[entries.length - 1].substring(0, 12) : null
});
```

```javascript
// Step 4b: Peek at the ending to verify natural conclusion
window._transcript.substring(window._transcript.length - 600);
```

### Step 5: Verify transcript completeness (MANDATORY)

Do all five checks before proceeding. Record actual values — they go directly into the output file's verification table.

1. **First timestamp** — starts at or near `[0:00]`
2. **Last timestamp** — within ~1–2 min of total video duration
3. **Ending content** — ends naturally (outro, sign-off, `[music]`), not mid-sentence
4. **Segment count** — reasonable for the video type:
   - Edited/polished videos: ~15–25 segments/min
   - Live streams & auto-generated captions: ~8–12 segments/min ← do not flag as an error
5. **Character count** — rough guide: ~800–2,500 chars/min depending on speech density

**If any check fails:** scroll the transcript panel to the bottom (forces lazy-load of remaining segments), then re-run Step 4. If still failing after one retry, proceed but set verification status to `⚠️ POTENTIALLY INCOMPLETE`.

### Step 6A: Deliver the file — Cowork / Claude Code (preferred, outputs .md)

Pull the transcript out of the browser via console chunking, then write the `.md` file directly to disk.

**6A-1: Log transcript chunks to console**
```javascript
console.clear();
var chunk = 5000;
var parts = Math.ceil(window._transcript.length / chunk);
for (var i = 0; i < parts; i++) {
  console.log('CHUNK_' + i + '_OF_' + (parts-1) + ':::' + window._transcript.substring(i*chunk, (i+1)*chunk));
}
'Logged ' + parts + ' chunks, ' + window._transcript.length + ' chars total';
```

**6A-2: Read all chunks**
```
Use read_console_messages with pattern: 'CHUNK_'
Read all returned messages and concatenate the content after each ':::' marker, in chunk order.
```

**6A-3: Write the .md file to disk**

Replace all CAPS placeholders with real values, paste in the reassembled transcript, and write to disk using `bash_tool` or `create_file`:

```bash
cat > ~/Desktop/youtube_transcript_SAFE_TITLE_DATE.md << 'ENDOFFILE'
# VIDEO_TITLE

**Channel:** CHANNEL_NAME
**Upload Date:** UPLOAD_DATE
**Duration:** DURATION
**URL:** VIDEO_URL
**Extracted:** EXTRACTION_DATE

---

## Transcript verification

**Status:** ✅ Complete

| Check | Result | Detail |
| --- | --- | --- |
| First timestamp at or near video start | ✅ | `FIRST_TS` |
| Last timestamp within ~1–2 min of duration | TS_CHECK | `LAST_TS` vs duration `DURATION` |
| Ends with natural conclusion (not mid-sentence) | END_CHECK | Last line: "LAST_LINE" |
| Segment count reasonable | SEG_CHECK | SEG_COUNT segs / DURATION_MINS min = SEG_PER_MIN/min |
| Character count plausible | CHAR_CHECK | CHAR_COUNT chars (~CHAR_PER_MIN/min) |

**Summary stats**
- Segments captured: SEG_COUNT
- Coverage: FIRST_TS → LAST_TS
- Total characters: CHAR_COUNT

---

## Transcript

FULL_TRANSCRIPT_HERE
ENDOFFILE
```

Save to the user's Desktop or working directory. Tell the user the file path.

---

### Step 6B: Deliver the file — Claude.ai (browser download, outputs .txt)

Assemble the full markdown and trigger a browser download in one JS call. **Replace all CAPS placeholders with the real values before running.**

```javascript
// ── Fill in these values before running ──────────────────────────────────
var VIDEO_TITLE     = "REPLACE";   // e.g. "End of War Trades"
var CHANNEL_NAME    = "REPLACE";   // e.g. "Dumb Money Live"
var UPLOAD_DATE     = "REPLACE";   // e.g. "Mar 23, 2026"  (human-readable, used in header)
var VIDEO_DATE      = "REPLACE";   // e.g. "2026-03-23"    (YYYY-MM-DD, used in filename)
var DURATION        = "REPLACE";   // e.g. "1:06:04"
var VIDEO_URL       = "REPLACE";   // full YouTube URL
var EXTRACTION_DATE = "REPLACE";   // e.g. "2026-05-06"
var DURATION_MINS   = 0;           // video length in decimal minutes e.g. 66.1
var FIRST_TS        = "REPLACE";   // e.g. "[0:00]"
var LAST_TS         = "REPLACE";   // e.g. "[1:05:56]"
var LAST_LINE       = "REPLACE";   // last meaningful line of transcript
var TS_CHECK        = "✅";        // ✅ or ❌
var END_CHECK       = "✅";
var SEG_CHECK       = "✅";
var CHAR_CHECK      = "✅";
var OVERALL_STATUS  = "✅ Complete"; // or "⚠️ POTENTIALLY INCOMPLETE"
var ISSUE_LINE      = "";           // set to "\n**Issue:** ..." if incomplete
// ─────────────────────────────────────────────────────────────────────────

// Auto-generate filename — .txt because Chrome on Mac blocks .md blob downloads
var safeTitle = VIDEO_TITLE.toLowerCase()
  .replace(/[^a-z0-9 ]/g, ' ').trim()
  .replace(/\s+/g, '_').substring(0, 60).replace(/_+$/, '');
var FILENAME = 'youtube_transcript_' + safeTitle + '_' + VIDEO_DATE + '.txt';

var segPerMin  = DURATION_MINS > 0 ? (window._transcriptSegmentCount / DURATION_MINS).toFixed(1) : "n/a";
var charPerMin = DURATION_MINS > 0 ? Math.round(window._transcriptCharCount / DURATION_MINS) : "n/a";

var chaptersSection = window._chapters
  ? "\n## Chapters / Key Moments\n\n" + window._chapters + "\n\n---\n"
  : "";

var md = `# ${VIDEO_TITLE}

**Channel:** ${CHANNEL_NAME}
**Upload Date:** ${UPLOAD_DATE}
**Duration:** ${DURATION}
**URL:** ${VIDEO_URL}
**Extracted:** ${EXTRACTION_DATE}

---

## Transcript verification

**Status:** ${OVERALL_STATUS}${ISSUE_LINE}

| Check | Result | Detail |
| --- | --- | --- |
| First timestamp at or near video start | ✅ | \`${FIRST_TS}\` |
| Last timestamp within ~1–2 min of duration | ${TS_CHECK} | \`${LAST_TS}\` vs duration \`${DURATION}\` |
| Ends with natural conclusion (not mid-sentence) | ${END_CHECK} | Last line: "${LAST_LINE}" |
| Segment count reasonable | ${SEG_CHECK} | ${window._transcriptSegmentCount} segs / ${DURATION_MINS} min = ${segPerMin}/min |
| Character count plausible | ${CHAR_CHECK} | ${window._transcriptCharCount} chars (~${charPerMin}/min) |

**Summary stats**
- Segments captured: ${window._transcriptSegmentCount}
- Coverage: ${FIRST_TS} → ${LAST_TS}
- Total characters: ${window._transcriptCharCount}

---
${chaptersSection}
## Transcript

${window._transcript}`;

var blob = new Blob([md], {type: 'text/plain'});
var url  = URL.createObjectURL(blob);
var a    = document.createElement('a');
a.href = url; a.download = FILENAME;
document.body.appendChild(a); a.click();
document.body.removeChild(a);
URL.revokeObjectURL(url);
'Downloaded: ' + md.length + ' chars → ' + FILENAME;
```

Confirm the JS returns `"Downloaded: N chars → filename"` and tell the user their file is in their **Downloads folder**. Remind them the content is markdown and can be renamed to `.md`.

## Output structure

````markdown
# {Video Title}

**Channel:** ...
**Upload Date:** ...
**Duration:** ...
**URL:** ...
**Extracted:** ...

---

## Transcript verification

**Status:** ✅ Complete

| Check | Result | Detail |
| --- | --- | --- |
| First timestamp at or near video start | ✅ | `[0:00]` |
| Last timestamp within ~1–2 min of duration | ✅ | `[1:05:56]` vs duration `1:06:04` |
| Ends with natural conclusion (not mid-sentence) | ✅ | Last line: "you have to be subscribed to find out" |
| Segment count reasonable | ✅ | 621 segs / 66 min = 9.4/min (auto-gen livestream) |
| Character count plausible | ✅ | 59,619 chars (~903/min) |

**Summary stats**
- Segments captured: 621
- Coverage: [0:00] → [1:05:56]
- Total characters: 59,619

---

## Chapters / Key Moments
*(section only present when the description contains timestamped chapter markers)*

[00:00] Preview
[00:35] The book that gave Jerry Seinfeld permission to pursue comedy
[02:56] AI bubble or not?
...

---

## Transcript

[0:00] First line of transcript...
[0:05] Second line...
...
[1:05:56] [music]
````

## Verification checklist

Fill the output table with actual observed values — not placeholders.

- [ ] First timestamp at or near video start
- [ ] Last timestamp within ~1–2 min of video duration
- [ ] Transcript ends with natural conclusion (not mid-sentence)
- [ ] Segment count reasonable for video type (8–25/min)
- [ ] Character count plausible (~800–2,500 chars/min)
- [ ] Chapters section included if markers found, omitted if not
- [ ] **Cowork/Claude Code:** file written to disk as `.md`, user told the path
- [ ] **Claude.ai:** browser download confirmed (JS returned char count), user told file is in Downloads as `.txt` (rename to `.md` to use as markdown)

## Important notes

- **YouTube has two transcript DOM architectures.** New videos use `transcript-segment-view-model` + `.ytwTranscriptSegmentViewModelTimestamp`; older videos use `ytd-transcript-segment-renderer` + `.segment-timestamp`. The Step 4 JS tries the new architecture first and falls back to the old one automatically. The JSON result includes an `architecture` field so you can confirm which path was taken.
- **JS tool output truncates at ~1000 chars** — never try to read the transcript back through it. Use console.log chunking (Step 6A) or the browser download (Step 6B).
- **Live streams / auto-gen captions produce ~8–12 segments/min** — normal, not a failure.
- If the video has no captions, stop and tell the user.
- `window._transcript` and `window._chapters` persist in the browser tab across Claude Desktop restarts.
- **Cowork / Claude Code → `.md` file written directly to disk.** No browser download needed.
- **Claude.ai → `.txt` browser download.** Chrome on Mac silently blocks `.md` blob downloads. Content is valid markdown; user can rename to `.md`.

## Example outputs

**Cowork (no chapters):**
Writes `youtube_transcript_end_of_war_trades_2026-03-23.md` to disk — metadata + verification table + transcript.

**Cowork (with chapters):**
Writes `youtube_transcript_bill_gurley_the_ai_era_10_days_in_china_life_less_2025-12-17.md` to disk — metadata + verification table + Chapters / Key Moments section + full transcript.

**Claude.ai (no chapters):**
Downloads `youtube_transcript_end_of_war_trades_2026-03-23.txt` — same content, `.txt` extension due to Chrome download restrictions. Rename to `.md` to use as markdown.
