---
name: redline
description: "Produce professional redlines (tracked changes) in two modes: (1) Word/OOXML tracked changes in .docx files via a reusable Python script, and (2) email-friendly inline redlines using strikethrough and bold formatting. Use this skill whenever a user wants to redline any business document — memos, proposals, contracts, board materials, marketing copy, policies, emails, or anything where the recipient needs to see exactly what changed. Also trigger on: 'redline this', 'track changes', 'mark up', 'show my edits', 'redline version', 'blackline', 'suggest changes', 'edit with tracked changes', 'review draft', 'propose edits', 'show changes inline', 'strikethrough', 'redline this email', 'mark up for email', 'show me the changes first', 'tighten this', 'improve this draft', or any request to edit a document with visible revisions. If the user uploads a .docx and asks you to improve, rewrite, tighten, or fix language, use this skill to deliver the edits as tracked changes unless they explicitly say otherwise. If the user pastes text or asks to show changes inline, email, or Slack, use Email Mode."
---

# Redline Skill

## Purpose

This skill produces professional redlines — clear, reviewable tracked changes for any business document: memos, proposals, contracts, emails, board materials, marketing copy, policies, or anything where the recipient needs to see exactly what changed. It works in **two modes**:

1. **Word Mode**: Proper OOXML tracked changes in .docx files. Deletions and insertions are marked at the XML level so the document opens in Word with full Track Changes functionality (accept/reject individual changes, filter by author, etc.). The primary path is the reusable script at `scripts/surgical_redline.py`.

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

- **Claude Code (CLI, desktop app, IDE):** Both modes work fully. Word Mode runs `scripts/surgical_redline.py` directly against the user's .docx.
- **claude.ai with code execution enabled:** Both modes work. Word Mode runs the script in the sandbox. The user uploads the .docx, the script writes the redlined .docx to `/mnt/user-data/outputs`, and it's returned via `present_files`.
- **claude.ai without code execution:** Email Mode only. `python-docx` — the only library available in pure-artifact environments — cannot produce OOXML tracked changes (it only supports comments). If the user needs a .docx with tracked changes and code execution isn't available, deliver the redline in Email Mode and offer to generate a copy of `surgical_redline.py` + the JSON edit list so they can run it locally.
- **Claude on mobile:** Email Mode markdown renders correctly. This is the primary use case — reviewing redlines on a phone.

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
1. **Preserve the original file** — the script never modifies the source. It unpacks to a temp working directory and writes a new .docx.
2. **Text in every `old` field of the edit list must be verbatim** — copied character-for-character from the original, including smart quotes, non-breaking spaces, and special characters. See Character Encoding Gotchas below.
3. **The script's revert logic is testable** — the XML it produces reverts cleanly to the original text when all tracked changes are rejected. If that's broken, the redline is broken.

### Email Mode

There is no .docx validator, so enforce control version integrity manually:

1. **Quote the original text first.** Before showing any redline, reproduce the exact passage being edited as the control version in a clearly labeled block:
   > **Original (control version):**
   > The company will invest $2.5M in platform modernization during FY2026...

2. **Struck-through text must be verbatim.** The text inside ~~strikethrough~~ markers (or `<span style="color:red;text-decoration:line-through;">`) must be copied character-for-character from the original. Do not paraphrase, summarize, or "clean up" inside deletion markers. If the original has a typo, the deletion has the typo.

3. **Validate the "clean read."** After producing the redline, construct the "accepted" version — the text you get by removing all ~~strikethrough~~ and keeping all **bold**. Verify it reads as grammatically correct, complete text with no words missing or duplicated at edit boundaries.

4. **For long passages, show the clean version.** When the redline is complex (5+ changes in one paragraph, or paragraph-level replacements), show the accepted version after the redline so the reader can sanity-check it.

5. **If the user provides the original text, quote it back before editing.** This confirms you have the right control version before you start marking it up.

### Multi-Round Editing: Edit First, Redline Last

The most common workflow is: the user works with Claude to improve a document over several rounds, THEN wants a clean redline at the end showing everything that changed from the original.

**The rule: lock the original at the start, keep it untouched through all rounds, redline against it at the end.**

1. **Lock the original.** When the user first provides the document, save it as the control version and quote it back in a clearly labeled block. This block is the anchor. It does not change regardless of how many rounds of editing follow.
2. **Edit freely.** Work with the user to improve the text. Show clean text during this phase — not redlined text. They're in "editing mode," not "review mode." Each round produces a new clean draft.
3. **Produce the redline at the end.** When the user says "show me what changed," "redline it," or "let me see the final vs original" — produce one redline comparing the locked original against the current final version. **Re-read the original from the locked block, not from memory.** After 3 rounds of editing, Claude's in-context memory of the original may have drifted.
4. **If the user wants incremental changes** (v2 → v3 instead of original → final), produce both, clearly labeled, so the reader knows which baseline they're looking at.

### Control Version Anti-Patterns

- **Paraphrasing inside deletions**: struck-through text doesn't match the original word-for-word. The redline is useless.
- **Silently fixing errors in the original**: if the original has "recieve," your deletion must show ~~recieve~~ not ~~receive~~. The correction is a separate tracked change: ~~recieve~~ **receive**.
- **Omitting the control version entirely** in email mode — jumping straight to the redline without establishing what the original was.
- **Letting the control version drift during multi-round editing** — using Claude's in-context memory of the original instead of the locked block.

## Summary of Changes (Required)

**Every redline must lead with a Summary of Changes.** The summary goes BEFORE the inline markup. This is what the reader looks at first — many will never scroll past it.

### Format

```
**Summary of Changes** ([N] edits)

1. **[Section/Location] (p.[page], ¶[paragraph])**: [What changed] — [old value] → [new value]
2. **[Section/Location] (p.[page], ¶[paragraph])**: [What changed] — [brief explanation]
```

When page numbers aren't available (plain text, email paste), use section headers and paragraph numbers counting from the top of that section.

### Example

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
- **Order by significance, not document order.** Put the most impactful change first.
- **Flag new sections and deleted sections explicitly.** "Added: Section 6 — Risk Factors (new)" or "Removed: Section 4.2 — Legacy Product Roadmap"
- **Make it forwarding-safe.** Someone receiving this third-hand should understand what changed from the summary alone.
- **Always include page and paragraph references.**

### Two-Document Comparison

When the user provides two versions of a document ("here's v2, here's v3 — what changed?"):

1. Read both versions fully before producing anything.
2. Diff them yourself — identify every substantive change (ignore whitespace, formatting, pagination).
3. Produce the Summary of Changes first, ordered by significance.
4. Then produce the inline markup against the earlier version as the control, using the later version as the target.
5. Flag ambiguous changes — if text was moved AND edited, call that out: "Moved from Section 2 to Section 5 AND revised (headcount changed from 20 → 15)."

### PDF-to-Redline Workflow

When the user provides a PDF (or two PDF versions) instead of a .docx:

1. **Extract the text.** Use the view tool or pdf-reading skill.
2. **Establish the control version.** Quote back the extracted text and confirm: "Here's what I extracted from pages 3-5. Is this accurate?" PDF text extraction can introduce errors (broken line breaks, missing characters, garbled tables) — catch them before they become fabricated deletions.
3. **Ask about output format.** Email Mode (faster, forwardable) or Word Mode (formal .docx, reconstructed from the extracted text then redlined via the script).
4. **Reference the PDF's page numbers** in the summary.

## Edit Plan Protocol

When the user's request is vague ("improve this section," "tighten the language," "clean up the draft"), present your planned edits before executing:

1. List each proposed change with its mode classification (word-level or paragraph-level)
2. For word-level: show the find → replace
3. For paragraph-level: summarize what's changing and why
4. Get user confirmation before executing

For explicit instructions ("change 30 to 60"), skip the plan and execute directly.

---

# Word Mode — OOXML Tracked Changes

Use this mode when producing a .docx file with proper tracked changes.

## Character Encoding Gotchas — READ FIRST

Business documents are full of smart punctuation that looks identical to ASCII but isn't. The #1 reason surgical edits fail is that the `old` text in the edit list has a regular character where the document has a Unicode variant. Always check for:

| Character | Unicode | Looks like |
|-----------|---------|------------|
| Non-breaking space | `\xa0` | regular space |
| Right single quote | `\u2019` | `'` — the smart apostrophe (extremely common) |
| Left single quote | `\u2018` | `` ` `` |
| Left double quote | `\u201C` | `"` |
| Right double quote | `\u201D` | `"` |
| En dash | `\u2013` | `-` |
| Em dash | `\u2014` | `--` |
| Ellipsis | `\u2026` | `...` |

**When the script's `replace` fails, it prints the near-match with hex codes.** Read the codes to spot the mismatch, then copy the exact characters into your edit list.

Example failure message the script produces:
```
✗ replace FAILED: 'cash savings'
  Near-match found but characters differ. Your needle: 'cash savings'
  Doc text: 'municated cash\xa0savings of $2.5M '
  Codes:    c(0x63) a(0x61) s(0x73) h(0x68)  (0xa0) s(0x73) a(0x61) v(0x76) ...
  HINT: Smart punctuation or non-breaking space mismatch.
```
Here the fix is to use `"cash\u00a0savings"` instead of `"cash savings"` in the edit list.

## The Default Path: Run the Script

For almost all Word Mode redlines, use the reusable script at `scripts/surgical_redline.py`. It handles run-splitting, ID management, `xml:space="preserve"`, formatting preservation, and encoding gotchas. You don't do XML surgery by hand unless the edit is genuinely outside the script's capabilities (see "When to drop to raw XML" below).

### Workflow

1. **Read the document.** Inspect paragraphs to find the exact wording of every passage you'll edit. A quick scan via `python-docx`:
   ```python
   from docx import Document
   for i, p in enumerate(Document("in.docx").paragraphs):
       print(f"{i}: {p.text!r}")
   ```
   The `!r` is important — it shows `\xa0` and smart quotes as escape sequences so you can see them.
2. **Build the edit list** as JSON or as a sequence of method calls on a `Redline` instance. Each edit is one of four types:
   - `replace` — word-level substitution
   - `paragraph_replace` — full paragraph swap with optional note
   - `insert_after` — new paragraph after a matched anchor
   - `insert_before` — new paragraph before a matched anchor
3. **Run the script.** Either CLI (`python scripts/surgical_redline.py --in in.docx --out out.docx --edits edits.json`) or library-style from inline Python.
4. **Read the report.** The script prints one line per edit with ✓ or ✗. Fix any failures by inspecting the hex codes in the diagnostic and correcting your edit list.
5. **Open in Word to verify visually** — especially for paragraph-level changes and inserted paragraphs.

### Library usage (preferred when you're writing Python inline)

```python
from surgical_redline import Redline

r = Redline("input.docx", author="JS Review", date="2026-04-16T12:00:00Z")

# Word-level edits
r.replace("monthly", "quarterly")
r.replace("$2.5M", "$3.1M")
r.replace("cash\u00a0savings", "net cash savings")   # note the \xa0
r.replace("We can\u2019t hunt elephants.",            # smart apostrophe
          "We will pursue larger opportunities selectively.")

# Paragraph-level replacement with note
r.paragraph_replace(
    anchor="The go-to-market strategy relies on",
    new_text="The go-to-market strategy combines a direct sales team of 15 reps...",
    note="Restructured GTM from pure direct sales to hybrid channel model."
)

# Pure paragraph insertion
r.insert_paragraph_after(
    anchor="execution sequence matters",
    text="The next 90 days are decisive..."
)

r.save("output.docx")
print(r.report())
```

### `anchor` parameter on `replace`

When the same phrase (e.g., "the Company") appears many times and you only want to change one instance, pass `anchor=` with a substring that uniquely identifies the target paragraph:

```python
r.replace("Company", "Buyer", anchor="representations and warranties")
```

### Paragraph-level notes

When you pass `note=` to `paragraph_replace`, the script inserts an italic `[Note: ...]` paragraph directly after the replaced paragraph, as a tracked insertion. This is the script's substitute for Word margin comments — cleaner than cluttering the replacement text, simpler than generating `comments.xml`. If you specifically need margin comments, run the docx skill's `comment.py` as a post-step.

### When to drop to raw XML

The script handles 95% of real-world redlines. Drop to manual XML editing (via `str_replace` on `document.xml`, following patterns in `references/redline-protocol.md`) only when:

- **Modifying another author's existing tracked change** (the script refuses to touch these — it's the safe default)
- **Cross-run edits where text spans multiple formatting contexts** and you want different formatting preserved in the deletion vs the insertion (e.g., the bold `(30)` example in `redline-protocol.md` §5)
- **Structural table changes** — inserting or deleting entire `<w:tr>` rows. The script edits cell *content* but not table structure.
- **Formatting-only tracked changes** (`<w:rPrChange>`) — rare, and most reviewers filter these out anyway.

For all of these, read `references/redline-protocol.md` for the XML patterns.

### Pre-redlined documents

If the source already contains tracked changes from another author, the script will refuse to edit text inside their `<w:ins>` or `<w:del>` blocks and will tell you so in the failure message. This is deliberate — modifying another author's tracked changes requires care. See `references/redline-protocol.md` §"Working with Pre-Redlined Documents" for the manual patterns (nesting `<w:del>` inside their `<w:ins>` to reject, etc.).

### Google Docs

Google Docs does not support OOXML tracked changes natively. If the user needs a Google Docs redline, produce the .docx and note that uploading to Google Docs will render it in Suggesting Mode.

---

# Email Mode — Inline Visual Redlines

Use this mode when showing changes in email bodies, Slack messages, conversation previews, or anywhere that doesn't support OOXML tracked changes. **This is the primary mode for most business communication** — memos sent to partners, board updates, management reports, and anything reviewed on a phone between meetings.

Detailed formatting patterns, worked examples, and common mistakes are in `references/email-redline-protocol.md`. This section covers the essentials.

## Principles for Business Redlines

**1. Lead with the Summary of Changes.** Always. The inline markup follows the summary. Many readers will act on the summary without scrolling to the markup.

**2. Make it forwarding-safe.** The redline will be forwarded to people who weren't on the original thread — board members, lenders, other partners. Every change must be self-explanatory.

**3. Numbers get special treatment.** When a dollar amount, percentage, headcount, date, or metric changes, always show old → new explicitly. "Revenue target: ~~$5.2M~~ **$4.1M**" is instantly scannable.

**4. Keep it scannable on mobile.** Assume the reader is on an iPhone between meetings. Use numbered changes, not long narrative paragraphs. One edit per line where possible. Keep lines under ~60 characters of visible text. No tables — they break on mobile. Never put a paragraph-level replacement inline in a dense paragraph; separate with blank lines.

## Markdown Sub-Mode (Default)

Use when showing changes in conversation, Slack, Teams, Discord, or any markdown-rendering context.

| Edit Type | Format | Example |
|-----------|--------|---------|
| Deletion | ~~strikethrough~~ | The term is ~~30~~ days |
| Insertion | **bold** | The term is **60** days |
| Replacement | ~~old~~ **new** | The term is ~~30~~ **60** days |
| Pure insertion | **bold** at insertion point | ...expenditures**, subject to Board approval,** up to $500K |
| Pure deletion | ~~strikethrough~~ | The Company ~~and any affiliated entities~~ shall comply |
| Comment | *[Note: explanation]* | *[Note: Changed per counterparty request]* |

### Paragraph-Level Replacement (Markdown)

> ~~The go-to-market strategy relies on a direct sales force of 20 reps targeting enterprise accounts in the Northeast, with a 12-month ramp period and a $50K average deal size.~~
>
> **The go-to-market strategy combines a direct sales team of 15 reps focused on mid-market accounts nationally, supplemented by channel partnerships with 3 regional resellers, targeting a $35K average deal size with a 6-month ramp period.**
>
> *[Note: Restructured GTM from pure direct sales to hybrid direct + channel model.]*

## HTML Sub-Mode (For Email Paste)

Use when the user needs to paste changes into an email body (Outlook, Gmail, Apple Mail). Markdown strikethrough does not render in most email clients — HTML with inline styles is required.

| Edit Type | HTML |
|-----------|------|
| Deletion | `<span style="color:red;text-decoration:line-through;">deleted</span>` |
| Insertion | `<span style="color:blue;font-weight:bold;text-decoration:underline;">new</span>` |
| Comment | `<span style="color:green;font-style:italic;">[Note: explanation]</span>` |

**Inline styles only** — email clients strip `<style>` blocks and external CSS.

See `references/email-redline-protocol.md` for full worked examples of every pattern.

## Email Mode Limitations

- **No accept/reject functionality** — email redlines are visual only.
- **No formatting tracking** — note formatting changes in a comment if they matter.
- **No structural changes** — describe table row additions/deletions in a comment.

## Complete Example: Board Memo Redline

> **⚠ Most Important Differences:**
> - Revenue forecast dropped 21% ($5.2M → $4.1M) — see p.3, ¶1
> - EBITDA margin compressed 4pts (18% → 14%) — see p.3, ¶2
> - New competitive threat: Competitor X closed $40M Series C — see p.7, ¶1
>
> **Summary of Changes** (5 edits to Q3 Board Memo v2 → v3)
>
> 1. **Revenue forecast (p.3, ¶1)**: Decreased — ~~$5.2M~~ → **$4.1M** (pipeline slippage in enterprise segment)
> 2. **EBITDA margin (p.3, ¶2)**: Decreased — ~~18%~~ → **14%**
> 3. **Headcount plan (p.5, ¶3)**: Reduced — ~~45 FTEs~~ → **38 FTEs** by Q4
> 4. **Product launch date (p.6, ¶1)**: Pushed — ~~September 2026~~ → **November 2026**
> 5. **Risk section (p.7, ¶1)**: Rewritten — added competitive threat from Competitor X Series C; removed supply chain risk (resolved)
>
> ---
>
> **Inline Markup:**
>
> The company projects ~~$5.2M~~ **$4.1M** in revenue for Q3, reflecting a ~~$700K~~ **$1.1M** shortfall against the original plan. EBITDA margin is expected to come in at ~~18%~~ **14%**...
>
> The v2.0 product launch is now targeted for ~~September~~ **November** 2026. *[Note: Pushed 2 months due to dependency on the platform migration completing in August.]*

---

# Preview-Then-Apply Workflow

This is the recommended workflow when the user uploads a .docx and gives a vague instruction. Show the changes first, get buy-in, then apply.

**Step 1: Show Changes (Email Mode — Markdown).** Present each proposed change using ~~strikethrough~~ / **bold**.

**Step 2: Get Approval.** Ask: "Want me to apply all of these to the .docx with tracked changes, or would you like to modify any?" Handle partial approval cleanly: "Apply all," "Skip #2," "Change #1 to 45 days," "Looks good but don't apply yet."

**Step 3: Apply to Document (Switch to Word Mode).** Take only the approved changes and apply them via the script. The approved changes from the conversation become the edit list — no re-classification needed since the edit-mode decisions were already made in Step 1.

**When to skip Preview:**
- User gives explicit instructions ("change 30 to 60")
- User explicitly asks for a .docx with tracked changes up front
- The edit is trivial (typo fix, single word swap)

---

# Quality Checklist (Both Modes)

For each change:

1. **Am I marking ONLY the words that change?** If you're wrapping a whole sentence in `<w:del>` or striking through a full paragraph when only one word changed, narrow scope.
2. **Did I classify the edit mode correctly?** Word-level vs. paragraph-level — apply the 40% / 5-second rule.
3. **If paragraph-level: did I attach a comment or explanatory note?**
4. **Does unchanged text remain in regular formatting**, untouched?

### Word Mode
5. Did the script's report show ✓ for every intended edit? Did I address every ✗ by reading the hex codes?
6. Did I open the output .docx in Word to verify visually?
7. For edits the script couldn't handle (cross-author changes, structural table edits), did I follow the XML patterns in `references/redline-protocol.md`?

### Email Mode
5. (Markdown) Are ~~strikethrough~~ and **bold** markers properly closed?
6. (HTML) Are all styles inline (not in a `<style>` block)?
7. (HTML) Do deletion and insertion spans have distinct colors (red vs blue)?
8. Is the redline readable in a single pass without cross-referencing?

## Anti-Patterns

**DO NOT:**

1. **Word-level tracking on a substantially rewritten paragraph** — produces unreadable tangle of red. Use paragraph-level replacement with a note.
2. **Paragraph-level replacement when only a word changed** — most common failure mode. If the change is "monthly" → "quarterly", delete "monthly" and insert "quarterly". Don't rewrite the whole sentence.
3. **Paragraph-level replacement without a note** — the reviewer has no way to understand intent.
4. **Marking unchanged text** — data integrity failure.
5. **(Word Mode) Hand-rolling XML edits when the script would handle them** — it handles run-splitting, IDs, encoding, and preservation correctly. Only drop to raw XML for the edge cases listed above.
6. **(Word Mode) Ignoring a ✗ in the script's report** — every failure is either a character-encoding issue (fix the edit list) or a genuine can't-do-this case (drop to raw XML with eyes open).
7. **(Email Mode) Using markdown strikethrough for email paste** — ~~strikethrough~~ does not render in Outlook, Gmail, or Apple Mail. Use HTML sub-mode.
8. **(Email Mode) Forgetting to close formatting markers** — bleeds into the rest of the text.
