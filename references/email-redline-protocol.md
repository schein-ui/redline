# Email Redline Protocol — Formatting Patterns and Worked Examples

## Table of Contents
1. [Control Version — Lock It In First](#control-version)
2. [Edit Mode Decision Framework](#decision-framework)
3. [Markdown Mode — Single Word Replacement](#md-single-word)
4. [Markdown Mode — Multi-Word Replacement](#md-multi-word)
5. [Markdown Mode — Pure Insertion](#md-insertion)
6. [Markdown Mode — Pure Deletion](#md-deletion)
7. [Markdown Mode — Paragraph-Level Replacement](#md-paragraph)
8. [Markdown Mode — Move Operations](#md-moves)
9. [Markdown Mode — Multiple Changes in One Passage](#md-batch)
10. [HTML Mode — Single Word Replacement](#html-single-word)
11. [HTML Mode — Multi-Word Replacement](#html-multi-word)
12. [HTML Mode — Pure Insertion](#html-insertion)
13. [HTML Mode — Pure Deletion](#html-deletion)
14. [HTML Mode — Paragraph-Level Replacement](#html-paragraph)
15. [HTML Mode — Move Operations](#html-moves)
16. [HTML Mode — Full Document Redline Example](#html-full)
17. [Common Mistakes and Fixes](#mistakes)

---

## 1. Control Version — Lock It In First <a name="control-version"></a>

Before producing any redline, establish the control version. This is the original, unmodified text that every deletion is measured against.

**Step 1: Quote the original.**
```
**Original (control version):**
Payment shall be made no later than thirty (30) calendar days after invoice receipt.
```

**Step 2: Produce the redline against that exact text.**
```
Payment shall be made ~~no later than thirty (30) calendar days~~ **within fifteen (15) business days** after invoice receipt.
```

**Step 3: Verify the clean read.** Remove all ~~strikethrough~~, keep all **bold**:
```
Payment shall be made within fifteen (15) business days after invoice receipt.
```
Does it read correctly? Grammatically complete? No missing words at edit boundaries? Good.

**The text inside ~~strikethrough~~ must be verbatim.** Character-for-character from the original. If the original has a typo, the deletion has the typo. If it uses smart quotes, the deletion uses smart quotes. Never paraphrase inside deletion markers.

---

## 2. Edit Mode Decision Framework <a name="decision-framework"></a>

The same decision tree from the main skill applies here. The only difference is the output format.

```
For each edit, ask:
  ├─ Is the change a targeted substitution (date, number, defined term, phrase)?
  │   └─ YES → Word-Level (inline strikethrough + bold)
  ├─ Are fewer than ~40% of the words in the paragraph changing?
  │   └─ YES → Word-Level (inline strikethrough + bold)
  ├─ Is the sentence structure preserved (same subject/verb/clause order)?
  │   └─ YES → Word-Level (inline strikethrough + bold)
  └─ Otherwise (substantial rewrite, reorganized clauses, combined/split sentences)
      └─ Paragraph-Level (full paragraph strikethrough + full paragraph bold + note)
```

### The 5-Second Rule

After mentally composing the tracked change, ask: **will a reviewer understand this edit in under 5 seconds?** If a word-level diff would require the reviewer to carefully reconstruct the before and after by mentally removing strikethroughs and assembling bold text, switch to paragraph-level with a note.

### Examples of Each Mode

**Word-level** (targeted, structure preserved):
- "Q3 2026" → "Q4 2026" ✓
- "$2.5M" → "$3.1M" ✓
- "15 reps" → "20 reps" ✓
- Adding ", subject to Board approval," after a budget line ✓
- Fixing a typo: "recieve" → "receive" ✓

**Paragraph-level** (structural rewrite):
- Rewriting a go-to-market section to change from direct sales to hybrid channel model ✓
- Splitting a run-on executive summary into three focused paragraphs ✓
- Reorganizing a budget table narrative to lead with ROI before listing costs ✓
- Completely replacing a risk section with updated competitive analysis ✓

---

## 3. Markdown Mode — Single Word Replacement <a name="md-single-word"></a>

**Scenario**: Change "monthly" to "quarterly" in "The report is distributed on a monthly basis."

**Output:**
```
The report is distributed on a ~~monthly~~ **quarterly** basis.
```

**What the reader sees**: The report is distributed on a ~~monthly~~ **quarterly** basis.

**Rules:**
- Strike through ONLY the word being replaced
- Bold ONLY the new word
- The replacement immediately follows the deletion (no extra spaces between ~~ and **)
- Unchanged text stays in normal formatting

---

## 4. Markdown Mode — Multi-Word Replacement <a name="md-multi-word"></a>

**Scenario**: Change "no later than thirty (30) calendar days" to "within fifteen (15) business days"

**Output:**
```
Payment shall be made ~~no later than thirty (30) calendar days~~ **within fifteen (15) business days** after invoice receipt.
```

**Rules:**
- Strike through the entire phrase being replaced, not individual words
- Bold the entire replacement phrase
- Keep the scope minimal — only the changing portion

---

## 5. Markdown Mode — Pure Insertion <a name="md-insertion"></a>

**Scenario**: Add ", subject to Board approval," after "The CEO may authorize expenditures"

**Output:**
```
The CEO may authorize expenditures**, subject to Board approval,** up to $500,000.
```

**Rules:**
- Bold the inserted text
- No strikethrough (nothing is being deleted)
- Position the bold text exactly where the insertion goes
- Include any necessary punctuation (commas, periods) inside the bold markers

---

## 6. Markdown Mode — Pure Deletion <a name="md-deletion"></a>

**Scenario**: Remove "and any affiliated entities" from the sentence

**Output:**
```
The Company ~~and any affiliated entities~~ shall comply with applicable law.
```

**Rules:**
- Strike through the deleted text
- No bold (nothing is being inserted)
- Include any trailing/leading spaces that should be removed inside the strikethrough

---

## 7. Markdown Mode — Paragraph-Level Replacement <a name="md-paragraph"></a>

**Scenario**: Rewriting a go-to-market strategy section (40%+ words changing, structure reorganized)

**Output:**
```
~~The go-to-market strategy relies on a direct sales force of 20 reps targeting enterprise accounts in the Northeast, with a 12-month ramp period and a $50K average deal size.~~

**The go-to-market strategy combines a direct sales team of 15 reps focused on mid-market accounts nationally, supplemented by channel partnerships with 3 regional resellers, targeting a $35K average deal size with a 6-month ramp period.**

*[Note: Restructured GTM from pure direct sales to hybrid direct + channel model. Reduced team size, broadened geography, shortened ramp, adjusted deal size target.]*
```

**Rules:**
- Strike through the ENTIRE old paragraph
- Bold the ENTIRE new paragraph
- Separate old and new with a blank line for readability
- ALWAYS include a *[Note: ...]* explaining what changed and why
- The note goes on its own line after the new paragraph

**Good note patterns:**
- "Rewrote to narrow scope from [X] to [Y]"
- "Restructured for clarity — substance unchanged"
- "Combined former sections 3.2 and 3.3 into single section"
- "Updated to reflect revised Q4 projections from finance"
- "Replaced enterprise-only strategy with hybrid enterprise + mid-market approach"

---

## 8. Markdown Mode — Move Operations <a name="md-moves"></a>

**Scenario**: Moving the risk factors from the Executive Summary to their own section

**At the source (Executive Summary):**
```
~~Key risks include competitive pressure from two well-funded entrants, dependency on a single distribution partner for 40% of revenue, and a 6-month window before the technology advantage erodes.~~ *[Note: Moved to Section 6 — Risk Factors]*
```

**At the destination (Section 6):**
```
**Key risks include competitive pressure from two well-funded entrants, dependency on a single distribution partner for 40% of revenue, and a 6-month window before the technology advantage erodes.** *[Note: Moved from Executive Summary]*
```

---

## 9. Markdown Mode — Multiple Changes in One Passage <a name="md-batch"></a>

**Scenario**: Three changes in one paragraph

**Output:**
```
The team will deliver ~~monthly~~ **quarterly** progress reports to the ~~Board of Directors~~ **Steering Committee** no later than the ~~15th~~ **20th** of each ~~month~~ **quarter**.
```

**Rules:**
- Each replacement is its own ~~old~~ **new** pair
- Don't merge adjacent changes — keep each atomic
- Read the result aloud to verify it flows naturally

---

## 10. HTML Mode — Single Word Replacement <a name="html-single-word"></a>

**Scenario**: Change "monthly" to "quarterly"

**Output:**
```html
<p>The report is distributed on a 
<span style="color:red;text-decoration:line-through;">monthly</span> 
<span style="color:blue;font-weight:bold;text-decoration:underline;">quarterly</span> 
basis.</p>
```

---

## 11. HTML Mode — Multi-Word Replacement <a name="html-multi-word"></a>

**Scenario**: Change "no later than thirty (30) calendar days" to "within fifteen (15) business days"

**Output:**
```html
<p>Payment shall be made 
<span style="color:red;text-decoration:line-through;">no later than thirty (30) calendar days</span> 
<span style="color:blue;font-weight:bold;text-decoration:underline;">within fifteen (15) business days</span> 
after invoice receipt.</p>
```

---

## 12. HTML Mode — Pure Insertion <a name="html-insertion"></a>

**Scenario**: Add ", subject to Board approval," after "The CEO may authorize expenditures"

**Output:**
```html
<p>The CEO may authorize expenditures<span style="color:blue;font-weight:bold;text-decoration:underline;">, subject to Board approval,</span> up to $500,000.</p>
```

---

## 13. HTML Mode — Pure Deletion <a name="html-deletion"></a>

**Scenario**: Remove "and any affiliated entities"

**Output:**
```html
<p>The Company <span style="color:red;text-decoration:line-through;">and any affiliated entities </span>shall comply with applicable law.</p>
```

---

## 14. HTML Mode — Paragraph-Level Replacement <a name="html-paragraph"></a>

**Scenario**: Rewriting a go-to-market strategy section

**Output:**
```html
<p style="color:red;text-decoration:line-through;">The go-to-market strategy relies on a direct sales force of 20 reps targeting enterprise accounts in the Northeast, with a 12-month ramp period and a $50K average deal size.</p>

<p><span style="color:blue;font-weight:bold;text-decoration:underline;">The go-to-market strategy combines a direct sales team of 15 reps focused on mid-market accounts nationally, supplemented by channel partnerships with 3 regional resellers, targeting a $35K average deal size with a 6-month ramp period.</span></p>

<p><span style="color:green;font-style:italic;">[Note: Restructured GTM from pure direct sales to hybrid direct + channel model. Reduced team size, broadened geography, shortened ramp.]</span></p>
```

---

## 15. HTML Mode — Move Operations <a name="html-moves"></a>

**At source (Executive Summary):**
```html
<p><span style="color:red;text-decoration:line-through;">Key risks include competitive pressure from two well-funded entrants, dependency on a single distribution partner for 40% of revenue, and a 6-month window before the technology advantage erodes.</span> 
<span style="color:green;font-style:italic;">[Note: Moved to Section 6]</span></p>
```

**At destination (Section 6):**
```html
<p><span style="color:blue;font-weight:bold;text-decoration:underline;">Key risks include competitive pressure from two well-funded entrants, dependency on a single distribution partner for 40% of revenue, and a 6-month window before the technology advantage erodes.</span> 
<span style="color:green;font-style:italic;">[Note: Moved from Executive Summary]</span></p>
```

---

## 16. HTML Mode — Full Document Redline Example <a name="html-full"></a>

**Scenario**: Three changes to a budget proposal section, mixing word-level and paragraph-level

```html
<div style="font-family: Georgia, serif; font-size: 11pt; line-height: 1.5;">

<p><b>3. Investment Timeline.</b> The project requires 
<span style="color:red;text-decoration:line-through;">$2.5M</span> 
<span style="color:blue;font-weight:bold;text-decoration:underline;">$3.1M</span> 
in total investment, deployed across 
<span style="color:red;text-decoration:line-through;">three phases over 18 months</span> 
<span style="color:blue;font-weight:bold;text-decoration:underline;">two phases over 12 months</span>, 
with Phase 1 beginning in 
<span style="color:red;text-decoration:line-through;">Q3 2026</span> 
<span style="color:blue;font-weight:bold;text-decoration:underline;">Q4 2026</span>.</p>

<p><b>4. Expected Returns.</b></p>

<p style="color:red;text-decoration:line-through;">We project a 3.2x return on investment over 36 months, driven primarily by new customer acquisition in the enterprise segment and a 15% reduction in customer acquisition cost through improved marketing automation.</p>

<p><span style="color:blue;font-weight:bold;text-decoration:underline;">We project a 2.8x return on investment over 24 months, driven by a combination of mid-market expansion (60% of projected returns) and operational efficiency gains from platform consolidation (40%). The accelerated timeline reflects the compressed two-phase approach.</span></p>

<p><span style="color:green;font-style:italic;">[Note: Revised ROI from 3.2x/36mo to 2.8x/24mo to reflect the two-phase timeline. Shifted return drivers from enterprise acquisition to mid-market + efficiency gains.]</span></p>

</div>
```

---

## 17. Common Mistakes and Fixes <a name="mistakes"></a>

### Mistake: Striking through too much text

**Wrong:**
```
~~The report is distributed on a monthly basis.~~ **The report is distributed on a quarterly basis.**
```
Only ONE word changed. This should be word-level, not paragraph-level.

**Right:**
```
The report is distributed on a ~~monthly~~ **quarterly** basis.
```

### Mistake: Missing the explanatory note on paragraph-level replacement

**Wrong:**
```
~~Old paragraph...~~

**New paragraph...**
```
The reviewer has no context for why the paragraph was rewritten.

**Right:**
```
~~Old paragraph...~~

**New paragraph...**

*[Note: Explanation of what changed and why]*
```

### Mistake: Using markdown strikethrough for email paste

Markdown ~~strikethrough~~ does NOT render in Outlook, Gmail, or Apple Mail. If the user is pasting into an email client, you MUST use HTML mode with inline styles.

### Mistake: Forgetting to close formatting markers

**Wrong:**
```
The term is ~~30 **60** days.
```
The strikethrough is never closed — it bleeds into the rest of the text.

**Right:**
```
The term is ~~30~~ **60** days.
```

### Mistake: Merging adjacent changes

**Wrong:**
```
~~The team will deliver monthly updates to the board~~ **The team will deliver quarterly updates to the steering committee**
```
Two separate changes (monthly→quarterly, board→steering committee) were merged into one paragraph-level swap. This hides the granularity of the edits.

**Right:**
```
The team will deliver ~~monthly~~ **quarterly** updates to the ~~board~~ **steering committee**
```

### Mistake: No visual separation in paragraph-level replacements

**Wrong (all runs together):**
```
~~Old long paragraph that goes on for several sentences about complex legal terms and conditions.~~ **New long paragraph that replaces the old one with different terms and a different structure.**
```

**Right (with blank line for readability):**
```
~~Old long paragraph that goes on for several sentences about complex legal terms and conditions.~~

**New long paragraph that replaces the old one with different terms and a different structure.**

*[Note: Explanation]*
```

### Mistake: Fabricating the control version

**Wrong (paraphrased deletion — not verbatim):**
```
The original said: "The Company shall make payment no later than thirty (30) calendar days"
But the redline shows: ~~The company will pay within 30 days~~ **The company will pay within 15 days**
```
The struck-through text doesn't match the original. This is a broken redline — the reviewer can't trust the deletions.

**Right (verbatim deletion):**
```
~~The Company shall make payment no later than thirty (30) calendar days~~ **The Company shall make payment within fifteen (15) business days**
```

### Mistake: Using external CSS in HTML mode

**Wrong:**
```html
<style>.del { color: red; text-decoration: line-through; }</style>
<p>The <span class="del">Company</span> shall comply.</p>
```
Email clients strip `<style>` blocks. The redline will render as plain text.

**Right:**
```html
<p>The <span style="color:red;text-decoration:line-through;">Company</span> shall comply.</p>
```
