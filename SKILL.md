---
name: redline
description: "Produce professional redlines (tracked changes) in two modes: (1) Word/OOXML tracked changes in .docx files, and (2) email-friendly inline redlines using strikethrough and bold formatting. Use this skill whenever a user wants to redline any business document — memos, proposals, contracts, board materials, marketing copy, policies, emails, or anything where the recipient needs to see exactly what changed. Also trigger on: 'redline this', 'track changes', 'mark up', 'show my edits', 'redline version', 'blackline', 'suggest changes', 'edit with tracked changes', 'review draft', 'propose edits', 'show changes inline', 'strikethrough', 'redline this email', 'mark up for email', 'show me the changes first', 'tighten this', 'improve this draft', or any request to edit a document with visible revisions. If the user uploads a .docx and asks you to improve, rewrite, tighten, or fix language, use this skill to deliver the edits as tracked changes unless they explicitly say otherwise. If the user pastes text or asks to show changes inline, email, or Slack, use Email Mode."
---

# Redline Skill

## Purpose

This skill produces professional redlines — clear, reviewable tracked changes for any business document: memos, proposals, contracts, emails, board materials, marketing copy, policies, or anything where the recipient needs to see exactly what changed. It works in **two modes**:

1. **Word Mode**: Proper OOXML tracked changes in .docx files. Deletions and insertions are marked at the XML level so the document opens in Word with full Track Changes functionality (accept/reject individual changes, filter by author, etc.).

2. **Email Mode**: Inline visual redlines using ~~strikethrough~~ for deletions and **bold** for insertions. Works in email bodies, Slack messages, conversation previews, and anywhere rich text or markdown renders. Two sub-modes: **Markdown** (default) and **HTML** (for email paste).

Both modes use the same edit-classification discipline — the same decision framework determines whether an edit is word-level or paragraph-level. Only the output format changes.

## Why This Matters

Without this discipline, the default behavior is to replace entire sentences or paragraphs with new content — even when only one word changed. In Word mode, this means wrapping whole `<w:r>` runs in `<w:del>` and `<w:ins>`. In email mode, this means striking through a full paragraph and bolding the replacement. The result looks like every sentence was rewritten. This is unprofessional, makes review painful, and destroys trust.

Conversely, forcing word-level tracking on a paragraph that's been completely restructured creates an unreadable mess of interleaved strikethroughs and insertions. The right approach uses both modes strategically — surgical precision where the change is small, clean replacement with an explanation where the rewrite is substantial.

## Mode Selection

### Auto-Detection (in priority order)

The default is Email Mode. Most business communication — memos, board updates, management reports — flows through email, Slack, and conversation. Word Mode is for when you need a .docx with formal tracked changes.

1. **User provides a .docx file AND asks for tracked changes** → Word Mode
2. **User provides a .docx file with a vague instruction** → Preview-Then-Apply (show changes in Email Mode first, then apply to .docx if approved)
3. **User says "for email," "paste into email," "HTML"** → Email Mode (HTML)
4. **User provides plain text, pastes document language, or asks to show changes** → Email Mode (Markdown)
5. **No file, no context clues** → Email Mode (Markdown)

### Explicit Override

The user can always override:
- "Use Word mode" / "tracked changes" / "produce a .docx" → Word Mode
- "Use markdown" / "show me inline" → Email Mode (Markdown)
- "Use HTML" / "for email" → Email Mode (HTML)

State the mode once at the start. Do not re-confirm for each edit.

### Platform Notes

- **Claude Code (CLI, desktop app, IDE):** Both Word Mode and Email Mode work fully. Word Mode uses the docx skill's unpack/edit/pack pipeline for surgical XML editing with validation.
- **claude.ai (web, Projects):** Email Mode works natively — ~~strikethrough~~ and **bold** render in the chat. PDF uploads work. Summary of Changes, Most Important Differences, all formatting conventions work. Word Mode works via artifacts — Claude can read an uploaded .docx, generate a new .docx with tracked changes in the XML, and output it as a downloadable artifact. The workflow is different (no unpack/pack scripts), but the same OOXML tracked-change XML patterns apply. For HTML sub-mode, Claude outputs the HTML code which the user copies and pastes into their email client.
- **Claude on mobile (claude.ai):** Email Mode markdown renders correctly. This is the primary use case — reviewing redlines on a phone.

## The Edit-Mode Decision Framework

**This framework applies to BOTH modes.** Before touching any paragraph, classify the edit:

**Use Word-Level Edits when:**
- Fewer than ~40% of the words in a sentence or paragraph are changing
- The edit is a targeted substitution: dates, numbers, defined terms, specific phrases
- The structural flow of the sentence is preserved — same subject, same verb pattern, same clause order
- A reviewer can glance at the change and immediately understand what moved

**Use Paragraph-Level Replacement when:**
- More than ~40% of the words are changing, OR the sentence structure is being reorganized
- The edit involves reordering clauses, combining sentences, or splitting a sentence into two
- Showing word-level diffs would produce a "wall of red" where the reviewer can't parse the before/after
- The reviewer would be better served by reading the old version, reading the new version, and seeing a note that explains the intent

The 40% threshold is a guideline, not a hard rule. The real test is: **will a reviewer looking at this change understand what happened in under 5 seconds?** If the word-level diff is clear at a glance, use word-level. If it's a mess, use paragraph-level with a comment.

**Mixed-mode within a single document is expected and professional.** A document redline might have 8 word-level changes (dates, names, figures) and 2 paragraph-level replacements (restructured sections), each with an explanatory note.

## Control Version Protocol

**Before making ANY edits, lock in the control version.** The control version is the original, unmodified text that your redline is measured against. Every deletion must be a verbatim copy of the original. Every "accept all changes" must produce coherent, grammatically correct text. If you can't reconstruct the original by reverting your changes, the redline is broken.

### Word Mode

The control version is the original .docx file itself:
1. **Preserve the original file** — never modify the source .docx directly. Unpack to a working directory.
2. **The `--original` flag locks it in** — when you run `pack.py unpacked/ output.docx --original document.docx`, the validator checks that reverting all tracked changes produces the original document text. If it doesn't, your redline introduced errors.
3. **Text inside `<w:delText>` must be verbatim** — copied character-for-character from the original run, including smart quotes, non-breaking spaces, and special characters. Do not paraphrase, clean up, or "fix" the original text inside deletion tags.

### Email Mode

There is no .docx validator, so you must enforce control version integrity manually:

1. **Quote the original text first.** Before showing any redline, reproduce the exact passage being edited as the control version. Present it in a clearly labeled block:
   > **Original (control version):**
   > The company will invest $2.5M in platform modernization during FY2026, with Phase 1 targeting the core ordering system and Phase 2 expanding to analytics and reporting.

2. **Struck-through text must be verbatim.** The text inside ~~strikethrough~~ markers (or `<span style="color:red;text-decoration:line-through;">`) must be copied character-for-character from the original. Do not paraphrase, summarize, or "clean up" the original inside deletion markers. If the original has a typo, the deletion has the typo. If the original uses "shall" and you're changing the verb, you strike through "shall" — not a reworded version.

3. **Validate the "clean read."** After producing the redline, mentally (or explicitly) construct the "accepted" version — the text you get by removing all ~~strikethrough~~ and keeping all **bold**. Verify:
   - It reads as grammatically correct, complete text
   - No words are missing or duplicated at edit boundaries
   - Spacing and punctuation are correct (no double spaces, no missing periods)

4. **For long passages, show the clean version.** When the redline is complex (5+ changes in one paragraph, or paragraph-level replacements), show the accepted version after the redline:
   > **Clean version (all changes accepted):**
   > The company will invest $3.1M in platform modernization during FY2026–2027, with Phase 1 targeting the core ordering system and Phase 2 expanding to analytics, reporting, and AI-powered recommendations.

5. **If the user provides the original text, quote it back before editing.** This confirms you have the right control version before you start marking it up. If the user pastes a paragraph and says "improve this," your first output should be the original quoted back, then the redline.

### Control Version Anti-Patterns

- **Paraphrasing inside deletions**: The struck-through text says "We'll spend $2.5M on tech" but the original said "The company will invest $2.5M in platform modernization during FY2026." This is a fabricated control version — the redline is useless.
- **Silently fixing errors in the original**: If the original has "recieve," your deletion must show ~~recieve~~ not ~~receive~~. The correction is a separate tracked change: ~~recieve~~ **receive**.
- **Omitting the control version entirely**: In email mode, jumping straight to the redline without establishing what the original text was. The reviewer has no way to verify the deletions are accurate.

## Summary of Changes (Required)

**Every redline must lead with a Summary of Changes.** The summary goes BEFORE the inline markup. This is what the reader looks at first — many will never scroll past it.

### Format

```
**Summary of Changes** ([N] edits)

1. **[Section/Location]**: [What changed] — [old value] → [new value]
2. **[Section/Location]**: [What changed] — [brief explanation]
3. **[Section/Location]**: [Paragraph rewritten] — [1-sentence summary of why]
```

### Example

> **Summary of Changes** (4 edits)
>
> 1. **Section 3 — Budget**: Total investment increased — $2.5M → $3.1M
> 2. **Section 3 — Timeline**: Launch pushed — Q3 2026 → Q4 2026
> 3. **Section 4 — GTM Strategy**: Paragraph rewritten — shifted from pure direct sales (20 reps, enterprise) to hybrid model (15 reps + 3 channel partners, mid-market)
> 4. **Section 5 — Headcount**: Sales team reduced — 20 → 15 (offset by channel partners)

### Format Details

Each line in the summary includes a **location reference** so the reader can jump straight to the source:

```
**Summary of Changes** ([N] edits)

1. **[Section/Location] (p.[page], ¶[paragraph])**: [What changed] — [old value] → [new value]
2. **[Section/Location] (p.[page], ¶[paragraph])**: [What changed] — [brief explanation]
```

When page numbers aren't available (plain text, email paste), use section headers and paragraph numbers counting from the top of that section.

### Example with Location References

> **Summary of Changes** (4 edits)
>
> 1. **Section 3 — Budget (p.4, ¶2)**: Total investment increased — $2.5M → $3.1M
> 2. **Section 3 — Timeline (p.4, ¶3)**: Launch pushed — Q3 2026 → Q4 2026
> 3. **Section 4 — GTM Strategy (p.6, ¶1)**: Paragraph rewritten — shifted from pure direct sales (20 reps, enterprise) to hybrid model (15 reps + 3 channel partners, mid-market)
> 4. **Section 5 — Headcount (p.8, ¶4)**: Sales team reduced — 20 → 15 (offset by channel partners)

### Most Important Differences (Required for 5+ changes)

When a redline has 5 or more changes, add a **"Most Important Differences"** callout at the very top of the summary — before the numbered list. This is the 10-second version for the reader who won't read past the first 3 lines.

```
**⚠ Most Important Differences:**
- Revenue forecast dropped 21% ($5.2M → $4.1M) — see p.3, ¶1
- Launch slipped 2 months (Sep → Nov 2026) — see p.5, ¶2
- New competitive threat added (Competitor X Series C) — see p.9, ¶1
```

**Rules for selecting "most important":**
- Any financial metric that moved more than 10% (revenue, EBITDA, margin, budget, headcount cost)
- Any timeline that shifted by more than 2 weeks
- Any new risk, removed commitment, or changed scope that would affect a board vote, lender covenant, or investment decision
- Cap at 3 items. If everything is important, nothing is. Pick the 3 the reader would call someone about.

### General Rules

- **Lead with numbers that changed.** If a dollar amount, date, headcount, or percentage moved, call it out with old → new. This is what the reader scans for.
- **Categorize paragraph rewrites in one sentence.** Don't describe every word — describe the *direction* of the change.
- **Order by significance, not document order.** Put the most impactful change first. If the revenue target dropped, that's #1 even if it's on page 5.
- **Flag new sections and deleted sections explicitly.** "Added: Section 6 — Risk Factors (new)" or "Removed: Section 4.2 — Legacy Product Roadmap"
- **Make it forwarding-safe.** Someone receiving this third-hand, with no context about prior versions, should understand what changed from the summary alone.
- **Always include page and paragraph references.** The reader needs to be able to flip to the exact spot in the document. If reviewing a printed memo in a board meeting, "p.4, ¶2" gets them there instantly.

### Two-Document Comparison

When the user provides two versions of a document ("here's v2, here's v3 — what changed?"), the workflow is:

1. **Read both versions fully** before producing anything.
2. **Diff them yourself** — identify every substantive change (ignore whitespace, formatting, pagination).
3. **Produce the Summary of Changes first**, ordered by significance.
4. **Then produce the inline markup** against the earlier version as the control, using the later version as the target.
5. **Flag ambiguous changes** — if text was moved AND edited, call that out: "Moved from Section 2 to Section 5 AND revised (headcount changed from 20 → 15)."

This is a common PE workflow: management sends a revised memo, the partner (or their chief of staff) needs to see what moved between versions before the board meeting.

### PDF-to-Redline Workflow

When the user provides a PDF (or two PDF versions) instead of a .docx:

1. **Extract the text.** Read the PDF using the Read tool. For long PDFs, read the specific pages/sections the user wants redlined.
2. **Establish the control version.** Quote back the extracted text and confirm with the user: "Here's what I extracted from pages 3-5. Is this accurate?" PDF text extraction can introduce errors (broken line breaks, missing characters, garbled tables) — catch them before they become fabricated deletions.
3. **Ask about output format.** "Want me to show the redline inline (for email/Slack), or produce a Word doc with tracked changes?" 
   - **Email Mode** — produce the redline as inline ~~strikethrough~~ / **bold** with Summary of Changes. Faster, good for review and forwarding.
   - **Word Mode** — create a new .docx from the extracted text, then apply tracked changes to it. The user gets a real Word document they can open, accept/reject changes, and send as an attachment. More formal, good for board packages and lender deliverables.
4. **Reference the PDF's page numbers.** Use the PDF's actual page numbers in the summary: "(p.4, ¶2)" means page 4 of the PDF, paragraph 2. The reader will have the PDF open alongside the redline.
5. **For two-PDF comparison:** Extract both, diff them, produce the Summary of Changes + Most Important Differences + inline markup against the earlier version as the control.

## Edit Plan Protocol

When the user's request is vague ("improve this section," "tighten the language," "clean up the draft"), present your planned edits before executing:

1. List each proposed change with its mode classification (word-level or paragraph-level)
2. For word-level: show the find → replace
3. For paragraph-level: summarize what's changing and why
4. Get user confirmation before executing

This is good professional practice — you don't just mark up the document, you explain your approach first. For explicit instructions ("change 30 to 60"), skip the plan and execute directly.

---

# Word Mode — OOXML Tracked Changes

Use this mode when producing a .docx file with proper tracked changes.

## Before You Start

1. Read the docx skill at `/mnt/skills/public/docx/SKILL.md` — specifically the "Editing Existing Documents" section (unpack → edit XML → pack) and the "XML Reference" section for tracked changes and comments. Skip "Creating New Documents" — it's not relevant here.
2. Read `references/redline-protocol.md` in this skill for detailed XML patterns and worked examples.
3. For character encoding (smart quotes, apostrophes, em-dashes), follow the docx skill's encoding table: `&#x2019;` for apostrophes, `&#x201C;`/`&#x201D;` for quotes, etc. Professional documents are full of these.

## Core Protocol

### Step 1: Extract and Map the Document

```bash
python /mnt/skills/public/docx/scripts/office/unpack.py document.docx unpacked/
```

Before making ANY edit, read `unpacked/word/document.xml` and build a mental map of the document's run structure. Understand how text is split across `<w:r>` elements. This mapping step is non-negotiable — you cannot do word-level edits without understanding the run boundaries.

### Step 2: Plan Edits and Classify Edit Mode

For each change the user requests, do two things:

**A) Classify the edit mode.** Apply the decision framework above:
- If the change is targeted (a few words, a number, a phrase swap) → **Word-Level Track Changes**
- If the paragraph is being substantially rewritten or restructured → **Paragraph-Level Replacement + Comment**

**B) Define the edit precisely.**

For **word-level edits**, define as a precise text substitution:
- **Find**: the exact words being replaced (minimum necessary scope)
- **Replace**: the new words
- Think of every edit as a `sed` operation. If you're changing "30 days" to "60 days", the Find is "30" and the Replace is "60". Not the whole sentence. Not the whole clause. Just "30" → "60".

For **paragraph-level edits**, define as:
- **Delete**: the entire paragraph content (wrapped in `<w:del>`)
- **Insert**: the full replacement paragraph (wrapped in `<w:ins>`)
- **Comment**: a 1-2 sentence explanation of what changed and why (anchored to the new paragraph)

### Step 3: Split Runs at Edit Boundaries

The hardest part of surgical redlining is that Word's XML doesn't store text word-by-word — it stores it in runs (`<w:r>`) that may contain entire sentences. To mark only specific words as changed, you must split the run:

**Before (one run containing "The term is 30 days"):**
```xml
<w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:t>The term is 30 days.</w:t></w:r>
```

**After (split into unchanged + deleted + inserted + unchanged):**
```xml
<w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:t xml:space="preserve">The term is </w:t></w:r>
<w:del w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:delText>30</w:delText></w:r>
</w:del>
<w:ins w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:t>60</w:t></w:r>
</w:ins>
<w:r><w:rPr><w:sz w:val="24"/></w:rPr><w:t xml:space="preserve"> days.</w:t></w:r>
```

**Critical rules for run splitting:**
1. **Preserve `<w:rPr>` formatting** — copy the original run's formatting properties into every split fragment, including the `<w:del>` and `<w:ins>` runs. If the original text was bold 12pt Arial, the tracked change must also be bold 12pt Arial.
2. **Add `xml:space="preserve"`** to any `<w:t>` element that has leading or trailing whitespace.
3. **Use `<w:delText>`** inside `<w:del>` blocks, never `<w:t>`.
4. **Unique `w:id` values** — every `<w:del>` and `<w:ins>` element needs a unique integer ID across the entire document.

### Step 4: Handle Edge Cases

**Change spans multiple runs:**
When the text you're changing crosses a run boundary (e.g., part is bold, part isn't), you need to handle each run separately. Delete the relevant portion of each run and insert the replacement adjacent to the first deletion.

**Deleting entire phrases or sentences:**
If removing a full clause, wrap only that clause's runs in `<w:del>`. Don't touch the surrounding runs.

**Adding new text (pure insertion, no deletion):**
Place a `<w:ins>` block at the insertion point — between existing runs, or by splitting a run at the insertion point.

**Inserting new paragraphs:**
To add a new paragraph, mark the paragraph break as inserted by putting `<w:ins/>` inside the new paragraph's `<w:pPr><w:rPr>`, and wrap the paragraph's content runs in `<w:ins>`. Do NOT wrap the entire `<w:p>` element in `<w:ins>` — `<w:ins>` is an inline element, not a block-level element.

**Deleting entire paragraphs:**
When removing all content from a paragraph, also mark the paragraph mark as deleted by adding `<w:del/>` inside `<w:pPr><w:rPr>`:
```xml
<w:p>
  <w:pPr>
    <w:rPr>
      <w:del w:id="3" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:del w:id="4" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:r><w:delText>Entire paragraph being removed...</w:delText></w:r>
  </w:del>
</w:p>
```

**Moving text (clause relocated from one section to another):**
Do NOT use Word's `<w:moveFrom>` / `<w:moveTo>` markup — it's complex, fragile, and renders inconsistently across Word versions. Instead, use two separate tracked changes: delete at the source location, insert at the destination. Add a comment at each location referencing the other (e.g., "Moved to Section 5.2" at the source, "Moved from Section 3.1" at the destination).

**Table cell edits:**
Edits inside table cells (`<w:tc>`) follow the same tracked-change patterns — same run-splitting, same `<w:del>`/`<w:ins>` rules. The tracked changes go inside the cell's `<w:p>` elements. You cannot delete or insert entire cells/rows via tracked changes (only their content); structural table changes require direct XML modification.

**Formatting-only changes:**
If you need to track a formatting change (e.g., bolding a defined term), OOXML supports `<w:rPrChange>` inside `<w:rPr>`. However, most reviewers filter out formatting changes in Word's Review pane. Only use formatting tracking if the user explicitly requests it.

### Step 5: Enable Track Revisions in Settings

Make sure `unpacked/word/settings.xml` includes `<w:trackRevisions/>` so Word opens the document in tracked-changes mode. Add it after `<w:proofState>` if not already present.

### Step 6: Pack and Validate

```bash
python /mnt/skills/public/docx/scripts/office/pack.py unpacked/ output.docx --original document.docx
```

The pack script runs validation including the redlining validator, which checks that reverting Claude's tracked changes produces the original document text. If validation fails, you introduced an error — probably modified text outside of tracked change tags or broke a run boundary.

## Adding Comments with Edits

When the user asks you to explain your changes, add comments anchored to the changed text using the comment.py script. See the docx skill for the comment workflow. Place `<w:commentRangeStart>` and `<w:commentRangeEnd>` around the tracked change to link the comment to the edit.

## Google Docs Considerations

Google Docs does not support OOXML tracked changes natively. If the user needs a Google Docs redline:
- Produce the .docx with tracked changes (the primary deliverable)
- Note that uploading to Google Docs will show tracked changes in Suggesting Mode format
- For native Google Docs editing, the user would need to use Suggesting Mode directly

## Working with Pre-Redlined Documents

If the document already contains tracked changes from another author:
- **Never modify text inside another author's `<w:ins>` or `<w:del>` tags**
- To reject another author's insertion: nest your `<w:del>` inside their `<w:ins>`
- To restore another author's deletion: add your `<w:ins>` after their `<w:del>`
- See the docx skill's XML Reference for patterns.

---

# Email Mode — Inline Visual Redlines

Use this mode when showing changes in email bodies, Slack messages, conversation previews, or anywhere that doesn't support OOXML tracked changes. **This is the primary mode for most business communication** — memos sent to partners, board updates, management reports, and anything reviewed on a phone between meetings.

## Before You Start

Read `references/email-redline-protocol.md` in this skill for detailed formatting patterns and worked examples.

## Principles for Business Redlines

**1. Lead with the Summary of Changes.** Always. The inline markup follows the summary, not the other way around. Many readers will act on the summary without scrolling to the markup.

**2. Make it forwarding-safe.** The redline will be forwarded to people who weren't on the original thread — board members, lenders, other partners. Every change must be self-explanatory. If someone reads just the redline with zero prior context, they should understand what changed and in which direction.

**3. Numbers get special treatment.** When a dollar amount, percentage, headcount, date, or metric changes, always show old → new explicitly. "Revenue target: ~~$5.2M~~ **$4.1M**" is instantly scannable. "The revenue projection was adjusted to reflect current pipeline" is not.

**4. Keep it scannable on mobile.** Assume the reader is on an iPhone between meetings. Before sending, mentally preview the output on a narrow screen. Specific rules:
- Use numbered changes, not long narrative paragraphs
- One edit per line where possible
- Bold the direction of change: **increased**, **decreased**, **pushed to Q4**, **removed**
- **Keep lines under ~60 characters of visible text.** On a phone, long lines wrap mid-word and break scannability
- **Never put a paragraph-level replacement inline in a dense paragraph.** On mobile, ~~a full struck-through paragraph followed by~~ **a full bold replacement paragraph** is an unreadable wall. Instead, separate them with blank lines and keep the note on its own line
- **No tables in email mode.** Tables break on mobile. Use numbered bullet points instead
- **Test: if you squint and can't tell what changed in 3 seconds, simplify the markup.** Move detail to the Summary of Changes and keep the inline markup minimal

## Markdown Sub-Mode (Default)

Use when showing changes in conversation, Slack, Teams, Discord, or any markdown-rendering context.

### Formatting Conventions

| Edit Type | Format | Example |
|-----------|--------|---------|
| **Deletion** | ~~strikethrough~~ | The term is ~~30~~ days |
| **Insertion** | **bold** | The term is **60** days |
| **Replacement** | ~~old~~ **new** | The term is ~~30~~ **60** days |
| **Pure insertion** | **bold** at insertion point | The CEO may authorize expenditures**, subject to Board approval,** up to $500,000 |
| **Pure deletion** | ~~strikethrough~~ | The Company ~~and any affiliated entities~~ shall comply |
| **Comment** | *[Note: explanation]* | *[Note: Changed per counterparty request]* |

### Paragraph-Level Replacement (Markdown)

When the edit-mode decision framework calls for paragraph-level replacement, show the full old paragraph struck through, the full new paragraph in bold, and an explanatory note:

> ~~The go-to-market strategy relies on a direct sales force of 20 reps targeting enterprise accounts in the Northeast, with a 12-month ramp period and a $50K average deal size.~~
>
> **The go-to-market strategy combines a direct sales team of 15 reps focused on mid-market accounts nationally, supplemented by channel partnerships with 3 regional resellers, targeting a $35K average deal size with a 6-month ramp period.**
>
> *[Note: Restructured GTM from pure direct sales to hybrid direct + channel model. Reduced team size, broadened geography, shortened ramp, adjusted deal size target.]*

### Move Operations (Markdown)

Show a deletion at the source with a note, and an insertion at the destination with a note:

> ~~Key risks include competitive pressure from two well-funded entrants and a 6-month window before the technology advantage erodes.~~ *[Note: Moved to Section 6 — Risk Factors]*
>
> [In Section 6:]
> **Key risks include competitive pressure from two well-funded entrants and a 6-month window before the technology advantage erodes.** *[Note: Moved from Executive Summary]*

## HTML Sub-Mode (For Email Paste)

Use when the user needs to paste changes into an email body (Outlook, Gmail, Apple Mail). Markdown strikethrough does not render in most email clients — HTML with inline styles is required.

### Formatting Conventions

| Edit Type | HTML |
|-----------|------|
| **Deletion** | `<span style="color:red;text-decoration:line-through;">deleted text</span>` |
| **Insertion** | `<span style="color:blue;font-weight:bold;text-decoration:underline;">new text</span>` |
| **Replacement** | Deletion span followed by insertion span |
| **Comment** | `<span style="color:green;font-style:italic;">[Note: explanation]</span>` |

**Why these styles:**
- **Red strikethrough** for deletions: Universal tracked-changes convention
- **Blue bold underline** for insertions: Mirrors Word's default tracked-change rendering
- **Green italic** for comments: Visually distinct from both edits
- **Inline styles only**: Email clients strip `<style>` blocks and external CSS

### Example: Full HTML Redline

```html
<p>The report is distributed on a 
<span style="color:red;text-decoration:line-through;">monthly</span> 
<span style="color:blue;font-weight:bold;text-decoration:underline;">quarterly</span> 
basis, due no later than 
<span style="color:red;text-decoration:line-through;">thirty (30) calendar</span> 
<span style="color:blue;font-weight:bold;text-decoration:underline;">fifteen (15) business</span> 
days after period end.</p>
```

### Paragraph-Level Replacement (HTML)

```html
<p style="color:red;text-decoration:line-through;">The go-to-market strategy relies on a direct 
sales force of 20 reps targeting enterprise accounts in the Northeast, with a 12-month ramp 
period and a $50K average deal size.</p>

<p><span style="color:blue;font-weight:bold;text-decoration:underline;">The go-to-market strategy 
combines a direct sales team of 15 reps focused on mid-market accounts nationally, supplemented 
by channel partnerships with 3 regional resellers, targeting a $35K average deal size with a 
6-month ramp period.</span></p>

<p><span style="color:green;font-style:italic;">[Note: Restructured GTM from pure direct sales 
to hybrid direct + channel model. Reduced team size, broadened geography, shortened ramp.]</span></p>
```

## Email Mode Limitations

- **No accept/reject functionality**: Email redlines are visual only. The recipient reads them, not clicks "Accept."
- **No formatting tracking**: You can't show that text was changed from italic to bold. Note formatting changes in a comment if they matter.
- **No structural changes**: Table row insertions/deletions can't be shown visually. Describe them in a comment.

## Complete Example: Board Memo Redline

This shows the full output a PE partner or CEO receives — summary first, then inline markup.

> **⚠ Most Important Differences:**
> - Revenue forecast dropped 21% ($5.2M → $4.1M) — see p.3, ¶1
> - EBITDA margin compressed 4pts (18% → 14%) — see p.3, ¶2
> - New competitive threat: Competitor X closed $40M Series C, targeting our segment — see p.7, ¶1
>
> **Summary of Changes** (5 edits to Q3 Board Memo v2 → v3)
>
> 1. **Revenue forecast (p.3, ¶1)**: Decreased — ~~$5.2M~~ → **$4.1M** (pipeline slippage in enterprise segment)
> 2. **EBITDA margin (p.3, ¶2)**: Decreased — ~~18%~~ → **14%** (reflects revised revenue + unchanged cost base)
> 3. **Headcount plan (p.5, ¶3)**: Reduced — ~~45 FTEs~~ → **38 FTEs** by Q4 (deferred 7 hires to Q1 2027)
> 4. **Product launch date (p.6, ¶1)**: Pushed — ~~September 2026~~ → **November 2026** (dependency on platform migration)
> 5. **Risk section (p.7, ¶1)**: Rewritten — added competitive threat from [Competitor X]'s Series C; removed supply chain risk (resolved)
>
> ---
>
> **Inline Markup:**
>
> The company projects ~~$5.2M~~ **$4.1M** in revenue for Q3, reflecting a ~~$700K~~ **$1.1M** shortfall against the original plan. EBITDA margin is expected to come in at ~~18%~~ **14%**, driven by the revenue miss against a ~~largely fixed~~ **largely unchanged** cost structure.
>
> We plan to end Q4 with ~~45~~ **38** FTEs, deferring ~~the remaining hires to H1 2027~~ **7 planned hires to Q1 2027 pending revenue recovery**.
>
> The v2.0 product launch is now targeted for ~~September~~ **November** 2026. *[Note: Pushed 2 months due to dependency on the platform migration completing in August. No change to feature scope.]*
>
> ~~Primary risks remain supply chain disruption and customer concentration. The top 5 accounts represent 62% of ARR, and any loss would materially impact the growth trajectory.~~
>
> **Primary risks are (1) competitive pressure from [Competitor X], which closed a $40M Series C in March and is targeting our mid-market segment, and (2) customer concentration, with the top 5 accounts representing 62% of ARR.** *[Note: Removed supply chain risk (resolved in Q2). Added competitive threat from Competitor X's Series C and mid-market push.]*

---

# Preview-Then-Apply Workflow

This is the recommended workflow when the user uploads a .docx and gives a vague instruction. Show the changes first, get buy-in, then apply.

## Step 1: Show Changes (Email Mode — Markdown)

Present each proposed change using ~~strikethrough~~ / **bold**:

> Here are my proposed changes to Section 3:
>
> 1. ~~Q3 2026~~ **Q4 2026** — aligning with the revised launch timeline
> 2. ~~$2.5M~~ **$3.1M** — reflecting the updated budget from finance
> 3. Paragraph replacement in the GTM section:
>    ~~The go-to-market strategy relies on a direct sales force of 20 reps...~~
>    **The go-to-market strategy combines a direct sales team of 15 reps...**
>    *[Note: Restructured GTM to hybrid direct + channel model]*

## Step 2: Get Approval

Ask: "Want me to apply all of these to the .docx with tracked changes, or would you like to modify any?"

**Handling partial approval:**
- "Apply all" → proceed with all changes
- "Skip #2, apply the rest" → apply only approved changes
- "Change #1 to 45 days instead" → update, confirm, apply
- "Looks good but don't apply yet" → the conversation serves as the redline record

## Step 3: Apply to Document (Switch to Word Mode)

Take only the approved changes and apply them using the Word Mode protocol. The approved changes from the conversation become the edit plan — no re-classification needed since the edit-mode decisions (word-level vs paragraph-level) were already made in Step 1.

## When to Default to Preview-Then-Apply

- User uploads a .docx with a vague instruction ("improve," "tighten," "clean up")
- User hasn't specified whether they want Word or email output
- The number of proposed changes is large (5+) and you want confirmation before XML surgery

## When to Skip Preview

- User gives explicit instructions ("change 30 to 60")
- User explicitly asks for a .docx with tracked changes
- The edit is trivial (typo fix, single word swap)

---

# Quality Checklist (Both Modes)

For each change you're about to make, verify:

1. **Am I marking ONLY the words that change?** This is the #1 failure mode. If you're wrapping a whole sentence in `<w:del>` or striking through a full paragraph when only one word changed, stop and narrow scope.
2. **Did I classify the edit mode correctly?** Word-level vs. paragraph-level — apply the 40% / 5-second rule.
3. **If paragraph-level: did I attach a comment or explanatory note?**
4. **Does unchanged text remain in regular formatting**, untouched?

### Word Mode Additional Checks
5. Did I preserve `<w:rPr>` formatting on all new runs (including inside `<w:del>` and `<w:ins>`)?
6. Did I use `<w:delText>` (not `<w:t>`) inside `<w:del>` blocks?
7. Did I add `xml:space="preserve"` on `<w:t>` / `<w:delText>` with leading or trailing whitespace?
8. Are my `w:id` values unique across the entire document?

### Email Mode Additional Checks
5. (Markdown) Are ~~strikethrough~~ and **bold** markers properly closed?
6. (HTML) Are all styles inline (not in a `<style>` block)?
7. (HTML) Do deletion and insertion spans have distinct colors (red vs blue)?
8. Is the redline readable in a single pass without cross-referencing?

## Error Recovery

### Word Mode
If a `str_replace` fails because the expected XML can't be found (often because a prior edit shifted the surrounding content):

1. Re-read the file with `view` — your earlier view output is stale after any successful edit.
2. Search for the target text content (not the XML structure) to re-locate it.
3. Reformulate the replacement using the current XML structure around that text.
4. If the text itself is gone (deleted by a prior edit), reassess whether the edit is still needed.

### Email Mode
If the user says the formatting looks wrong:
1. Check that all ~~strikethrough~~ and **bold** markers are properly paired.
2. If pasting into email, switch from Markdown to HTML sub-mode.
3. If HTML renders incorrectly, verify inline styles (no external CSS references).

## Anti-Patterns (Things That Make Redlines Unprofessional)

**DO NOT** do any of these:

1. **Word-level tracking on a substantially rewritten paragraph**: If 60%+ of the words changed and the sentence structure is different, the result is an unreadable tangle of red. Use paragraph-level replacement with a comment instead.

2. **Paragraph-level replacement when only a word changed**: The opposite mistake. If the user says "change 'monthly' to 'quarterly'", you delete "monthly" and insert "quarterly". You do NOT delete the whole sentence and rewrite it. This is the most common failure mode.

3. **Paragraph-level replacement WITHOUT a comment/note**: If you do replace a full paragraph, the reviewer has no way to understand the intent without a comment. Always attach one explaining what changed and why.

4. **Marking unchanged text**: Wrapping text that didn't change in deletion + insertion markup. This is a data integrity failure.

5. **(Word Mode) Losing formatting**: Forgetting to copy `<w:rPr>` into tracked change runs. The tracked changes will render in default font/size, looking broken.

6. **(Word Mode) Forgetting `xml:space="preserve"`**: Leading/trailing spaces disappear, words run together.

7. **(Email Mode) Using markdown strikethrough for email paste**: ~~strikethrough~~ does not render in Outlook, Gmail, or Apple Mail. Use HTML sub-mode when the output is going into an actual email client.

8. **(Email Mode) Forgetting to close formatting markers**: Unclosed ~~strikethrough or **bold** bleeds into the rest of the text, making the entire passage unreadable.
