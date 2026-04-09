# Redline Protocol — Detailed XML Patterns and Examples

## Table of Contents
1. [Edit Mode Decision Framework](#decision-framework)
2. [Anatomy of a Surgical Edit](#anatomy)
3. [Single Word Replacement](#single-word)
4. [Multi-Word Phrase Replacement](#multi-word)
5. [Cross-Run Edits](#cross-run)
6. [Pure Insertions](#insertions)
7. [Pure Deletions](#deletions)
8. [Paragraph Deletion](#paragraph-deletion)
9. [Paragraph-Level Replacement with Comment](#paragraph-replacement)
10. [Paragraph Insertion](#paragraph-insertion)
11. [Move Operations](#move-operations)
12. [Table Cell Edits](#table-cells)
13. [Batch Editing Workflow](#batch-workflow)
14. [Common Mistakes and Fixes](#mistakes)

---

## 1. Edit Mode Decision Framework <a name="decision-framework"></a>

Not every edit should be word-level. The goal is reviewer clarity, and sometimes a clean paragraph swap with a comment is clearer than 30 interleaved tracked changes.

### Decision Tree

```
For each edit, ask:
  ├─ Is the change a targeted substitution (date, number, defined term, phrase)?
  │   └─ YES → Word-Level Track Changes
  ├─ Are fewer than ~40% of the words in the paragraph changing?
  │   └─ YES → Word-Level Track Changes
  ├─ Is the sentence structure preserved (same subject/verb/clause order)?
  │   └─ YES → Word-Level Track Changes
  └─ Otherwise (substantial rewrite, reorganized clauses, combined/split sentences)
      └─ Paragraph-Level Replacement + Comment
```

### The 5-Second Rule

After mentally composing the tracked change, ask: **will a reviewer understand this edit in under 5 seconds?** If a word-level diff would require the reviewer to carefully reconstruct the before and after by mentally removing strikethroughs and assembling insertions, switch to paragraph-level with a comment.

### Examples of Each Mode

**Word-level** (targeted, structure preserved):
- "30 days" → "60 days" ✓
- "the Company" → "the Buyer" ✓  
- "shall use best efforts" → "shall use commercially reasonable efforts" ✓
- Adding ", subject to Board approval," after a clause ✓
- Fixing a typo: "recieve" → "receive" ✓

**Paragraph-level** (structural rewrite):
- Rewriting an indemnification clause to narrow scope from all damages to direct damages only, changing the cap structure, and adding a basket — the clause is fundamentally different ✓
- Splitting a run-on paragraph into three shorter paragraphs ✓
- Reorganizing a termination provision to put cure periods before termination triggers ✓
- Completely replacing boilerplate governing law language with a different jurisdiction's standard ✓

---

## 2. Anatomy of a Surgical Edit <a name="anatomy"></a>

Every redline edit follows this pattern:

```
[unchanged prefix run] → [w:del of old text] → [w:ins of new text] → [unchanged suffix run]
```

The key insight: you are **splitting** an existing `<w:r>` element into up to four pieces. The original run's `<w:rPr>` (formatting) must be preserved on every piece.

### ID Management

Each `<w:del>` and `<w:ins>` element requires a unique `w:id` attribute (integer). Before editing, scan the document for the highest existing `w:id` value and start your IDs above that. A simple approach:

```bash
grep -oP 'w:id="\K[^"]+' unpacked/word/document.xml | sort -n | tail -1
```

Add 100 to the result and count up from there.

### Timestamp

Use a consistent ISO 8601 timestamp for all your changes:
```
w:date="2025-01-01T00:00:00Z"
```

### Author

Default to `w:author="Claude"` unless the user specifies otherwise.

---

## 3. Single Word Replacement <a name="single-word"></a>

**Scenario**: Change "monthly" to "quarterly" in "The report is distributed on a monthly basis."

**Original XML:**
```xml
<w:r>
  <w:rPr><w:rFonts w:ascii="Arial"/><w:sz w:val="24"/></w:rPr>
  <w:t>The report is distributed on a monthly basis.</w:t>
</w:r>
```

**Step 1**: Identify the target word and its position in the text string.
- Prefix: "The report is distributed on a "
- Target: "monthly"
- Suffix: " basis."

**Step 2**: Split into four runs:

```xml
<w:r>
  <w:rPr><w:rFonts w:ascii="Arial"/><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve">The report is distributed on a </w:t>
</w:r>
<w:del w:id="101" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:rFonts w:ascii="Arial"/><w:sz w:val="24"/></w:rPr>
    <w:delText>monthly</w:delText>
  </w:r>
</w:del>
<w:ins w:id="102" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:rFonts w:ascii="Arial"/><w:sz w:val="24"/></w:rPr>
    <w:t>quarterly</w:t>
  </w:r>
</w:ins>
<w:r>
  <w:rPr><w:rFonts w:ascii="Arial"/><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve"> basis.</w:t>
</w:r>
```

**What the reviewer sees in Word**: "The report is distributed on a ~~monthly~~ quarterly basis."

---

## 4. Multi-Word Phrase Replacement <a name="multi-word"></a>

**Scenario**: Change "no later than thirty (30) calendar days" to "within fifteen (15) business days"

**Original XML:**
```xml
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t>Payment shall be made no later than thirty (30) calendar days after invoice receipt.</w:t>
</w:r>
```

**Split at phrase boundaries:**
```xml
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve">Payment shall be made </w:t>
</w:r>
<w:del w:id="101" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:sz w:val="24"/></w:rPr>
    <w:delText>no later than thirty (30) calendar days</w:delText>
  </w:r>
</w:del>
<w:ins w:id="102" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:sz w:val="24"/></w:rPr>
    <w:t>within fifteen (15) business days</w:t>
  </w:r>
</w:ins>
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve"> after invoice receipt.</w:t>
</w:r>
```

---

## 5. Cross-Run Edits <a name="cross-run"></a>

**Scenario**: The text "thirty (30)" spans two runs — "thirty" is in normal text, "(30)" is bold.

**Original XML:**
```xml
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve">Payment due in thirty </w:t>
</w:r>
<w:r>
  <w:rPr><w:sz w:val="24"/><w:b/></w:rPr>
  <w:t>(30)</w:t>
</w:r>
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve"> calendar days.</w:t>
</w:r>
```

**To change "thirty (30)" to "fifteen (15)":**

You need to split the first run to isolate "thirty ", delete it, then delete the bold "(30)" run, then insert the replacement:

```xml
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve">Payment due in </w:t>
</w:r>
<w:del w:id="101" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:sz w:val="24"/></w:rPr>
    <w:delText xml:space="preserve">thirty </w:delText>
  </w:r>
</w:del>
<w:del w:id="102" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:sz w:val="24"/><w:b/></w:rPr>
    <w:delText>(30)</w:delText>
  </w:r>
</w:del>
<w:ins w:id="103" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:sz w:val="24"/></w:rPr>
    <w:t xml:space="preserve">fifteen </w:t>
  </w:r>
  <w:r>
    <w:rPr><w:sz w:val="24"/><w:b/></w:rPr>
    <w:t>(15)</w:t>
  </w:r>
</w:ins>
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve"> calendar days.</w:t>
</w:r>
```

Note: The insertion preserves the formatting split — "fifteen " in normal, "(15)" in bold — to match the original formatting intent.

---

## 6. Pure Insertions <a name="insertions"></a>

**Scenario**: Add ", subject to Board approval," after "The CEO may authorize expenditures"

**Original XML:**
```xml
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t>The CEO may authorize expenditures up to $500,000.</w:t>
</w:r>
```

**Split at insertion point and add `<w:ins>`:**
```xml
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t>The CEO may authorize expenditures</w:t>
</w:r>
<w:ins w:id="101" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:sz w:val="24"/></w:rPr>
    <w:t>, subject to Board approval,</w:t>
  </w:r>
</w:ins>
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve"> up to $500,000.</w:t>
</w:r>
```

---

## 7. Pure Deletions <a name="deletions"></a>

**Scenario**: Remove "and any affiliated entities" from a sentence.

**Original:**
```xml
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t>The Company and any affiliated entities shall comply with applicable law.</w:t>
</w:r>
```

**Split and wrap deleted phrase:**
```xml
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t xml:space="preserve">The Company </w:t>
</w:r>
<w:del w:id="101" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r>
    <w:rPr><w:sz w:val="24"/></w:rPr>
    <w:delText xml:space="preserve">and any affiliated entities </w:delText>
  </w:r>
</w:del>
<w:r>
  <w:rPr><w:sz w:val="24"/></w:rPr>
  <w:t>shall comply with applicable law.</w:t>
</w:r>
```

---

## 8. Paragraph Deletion <a name="paragraph-deletion"></a>

When deleting an entire paragraph, you must also mark the paragraph mark as deleted so accepting the deletion merges paragraphs correctly:

```xml
<w:p>
  <w:pPr>
    <w:rPr>
      <w:del w:id="101" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:del w:id="102" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:r>
      <w:rPr><w:sz w:val="24"/></w:rPr>
      <w:delText>This entire paragraph is being removed.</w:delText>
    </w:r>
  </w:del>
</w:p>
```

Without the `<w:del/>` in `<w:pPr><w:rPr>`, accepting the change leaves an empty paragraph behind.

---

## 9. Paragraph-Level Replacement with Comment <a name="paragraph-replacement"></a>

When a paragraph has been substantially rewritten (40%+ of words changed, clause structure reorganized), use this pattern instead of word-level tracking. The combination of delete-old + insert-new + explanatory comment is clearer for the reviewer.

**Scenario**: Rewriting an indemnification clause to narrow scope from "all losses" to "direct damages only" and adding a cap.

**Original paragraph XML (simplified):**
```xml
<w:p>
  <w:pPr><w:pStyle w:val="BodyText"/></w:pPr>
  <w:r>
    <w:rPr><w:sz w:val="24"/></w:rPr>
    <w:t>Seller shall indemnify and hold harmless the Buyer from and against any and all losses, damages, liabilities, costs, and expenses arising out of or relating to any breach of this Agreement.</w:t>
  </w:r>
</w:p>
```

**After (deleted old paragraph, inserted new paragraph, attached comment):**

First, run comment.py to create the comment:
```bash
python /mnt/skills/public/docx/scripts/comment.py unpacked/ 0 "Narrowed indemnification to direct damages only, added $5M aggregate cap, and excluded consequential damages. Original covered all losses without cap."
```

Then edit document.xml:
```xml
<w:p>
  <w:pPr>
    <w:pStyle w:val="BodyText"/>
    <w:rPr>
      <w:del w:id="101" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:commentRangeStart w:id="0"/>
  <w:del w:id="102" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:r>
      <w:rPr><w:sz w:val="24"/></w:rPr>
      <w:delText>Seller shall indemnify and hold harmless the Buyer from and against any and all losses, damages, liabilities, costs, and expenses arising out of or relating to any breach of this Agreement.</w:delText>
    </w:r>
  </w:del>
</w:p>
<w:p>
  <w:pPr>
    <w:pStyle w:val="BodyText"/>
    <w:rPr>
      <w:ins w:id="103" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:ins w:id="104" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:r>
      <w:rPr><w:sz w:val="24"/></w:rPr>
      <w:t>Seller shall indemnify the Buyer for direct damages arising from a breach of this Agreement, subject to an aggregate cap of $5,000,000. In no event shall Seller be liable for consequential, incidental, or punitive damages.</w:t>
    </w:r>
  </w:ins>
  <w:commentRangeEnd w:id="0"/>
  <w:r>
    <w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>
    <w:commentReference w:id="0"/>
  </w:r>
</w:p>
```

**What the reviewer sees**: The old paragraph struck through, the new paragraph underlined/colored, and a margin comment balloon reading: "Narrowed indemnification to direct damages only, added $5M aggregate cap, and excluded consequential damages. Original covered all losses without cap."

**Why this is better than word-level here**: The clause went from a single broad indemnification to a narrowed scope + cap + carve-out. Trying to show this as word-level diffs would create an unreadable mess of interleaved red text. The paragraph-level swap with comment lets the reviewer read each version cleanly and understand the intent from the comment.

### When to Attach Comments

Comments should accompany paragraph-level replacements to explain the *intent* behind the change. Good comment patterns:

- "Rewrote to narrow scope from [X] to [Y]"
- "Restructured for clarity — substance unchanged"
- "Combined former sections 3.2(a) and 3.2(b) into single provision"
- "Replaced governing law from [State A] to [State B] per counterparty request"
- "Added mutual indemnification — original was one-directional"

Comments are optional for word-level edits (the change itself is self-explanatory) but can be added when context helps, such as "Updated to reflect the revised closing date."

---

## 10. Paragraph Insertion <a name="paragraph-insertion"></a>

To insert a new paragraph, mark the paragraph break as inserted via `<w:ins/>` in the paragraph's `<w:pPr><w:rPr>`, and wrap the content runs in `<w:ins>`. Do NOT wrap the entire `<w:p>` element in `<w:ins>` — `<w:ins>` is an inline (run-level) element, not a block-level element.

```xml
<w:p>
  <w:pPr>
    <w:rPr>
      <w:ins w:id="101" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:ins w:id="102" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:r>
      <w:rPr><w:sz w:val="24"/></w:rPr>
      <w:t>This is a newly inserted paragraph.</w:t>
    </w:r>
  </w:ins>
</w:p>
```

The `<w:ins/>` in `<w:pPr><w:rPr>` marks the paragraph break itself as inserted. The `<w:ins>` around the content runs marks the text as inserted. Both are required — without the paragraph-mark insertion, accepting the change would leave the paragraph break as if it always existed.

---

## 11. Move Operations <a name="move-operations"></a>

When relocating text from one section to another (e.g., moving a definition from Section 1 to Section 8), do NOT use Word's `<w:moveFrom>` / `<w:moveTo>` markup. It requires matching range IDs, paired start/end markers at both source and destination, and many Word versions render it inconsistently or corrupt it on save.

**Instead, use two separate tracked changes:**

1. **At the source**: Delete the text with `<w:del>` and add a comment: "Moved to Section [X]"
2. **At the destination**: Insert the text with `<w:ins>` and add a comment: "Moved from Section [Y]"

This is how experienced contract redliners handle moves in practice. The reviewer sees a deletion, an insertion, and paired comments that explain the relationship.

---

## 12. Table Cell Edits <a name="table-cells"></a>

Edits inside table cells follow the same tracked-change patterns as regular paragraphs. The `<w:del>` and `<w:ins>` elements go inside the cell's `<w:p>` elements, using the same run-splitting technique.

Key constraint: you cannot insert or delete entire rows or cells via tracked changes alone (only their text content). To add a row to a pricing table, you would need to add the `<w:tr>` directly to the XML and mark each cell's content as inserted. To delete a row, mark all cell content as deleted and add a comment noting the structural change.

---

## 13. Batch Editing Workflow <a name="batch-workflow"></a>

When making multiple edits to a document:

1. **Plan all edits first** — list every change before touching XML.
2. **Work bottom-to-top** — start from the end of the document and work backward. This prevents earlier edits from shifting the character positions of later ones.
3. **Use the str_replace tool** — for each edit, use `str_replace` to find the exact XML of the original run and replace it with the split version. This is safer than writing Python scripts.
4. **One edit per str_replace** — don't try to combine multiple edits into one replacement. Keep them atomic.
5. **Re-read the file between edits** — after each str_replace, view the file again before making the next edit. Earlier str_replace output is stale.

### Example Batch Session

```
User: "In section 3.1, change 'monthly' to 'quarterly' and change '30 days' to '15 business days'"

Plan:
  Edit 1: "30 days" → "15 business days" (later in document, do first)
  Edit 2: "monthly" → "quarterly" (earlier in document, do second)

Execute:
  1. View document.xml, find the run containing "30 days"
  2. str_replace: split that run, wrap "30 days" in w:del, add "15 business days" in w:ins
  3. View document.xml again (stale after edit)
  4. Find the run containing "monthly"
  5. str_replace: split that run, wrap "monthly" in w:del, add "quarterly" in w:ins
```

---

## 14. Common Mistakes and Fixes <a name="mistakes"></a>

### Mistake: Forgetting xml:space="preserve"

**Wrong:**
```xml
<w:r><w:t>The term is </w:t></w:r>
```
The trailing space will be stripped. Word renders "The term is60 days."

**Right:**
```xml
<w:r><w:t xml:space="preserve">The term is </w:t></w:r>
```

### Mistake: Using `<w:t>` inside `<w:del>`

**Wrong:**
```xml
<w:del w:id="1" w:author="Claude" w:date="...">
  <w:r><w:t>deleted text</w:t></w:r>
</w:del>
```

**Right:**
```xml
<w:del w:id="1" w:author="Claude" w:date="...">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
```

### Mistake: Nesting `<w:del>` or `<w:ins>` inside `<w:r>`

**Wrong:**
```xml
<w:r>
  <w:t>The term is </w:t>
  <w:del w:id="1" w:author="Claude" w:date="...">
    <w:delText>30</w:delText>
  </w:del>
</w:r>
```

**Right:** `<w:del>` and `<w:ins>` are siblings of `<w:r>`, never children:
```xml
<w:r><w:t xml:space="preserve">The term is </w:t></w:r>
<w:del w:id="1" w:author="Claude" w:date="...">
  <w:r><w:delText>30</w:delText></w:r>
</w:del>
```

### Mistake: Dropping formatting on tracked change runs

**Wrong (no rPr on del/ins runs):**
```xml
<w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t xml:space="preserve">The </w:t></w:r>
<w:del w:id="1" w:author="Claude" w:date="...">
  <w:r><w:delText>old</w:delText></w:r>  <!-- Missing formatting! -->
</w:del>
```

**Right:**
```xml
<w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:t xml:space="preserve">The </w:t></w:r>
<w:del w:id="1" w:author="Claude" w:date="...">
  <w:r><w:rPr><w:b/><w:sz w:val="28"/></w:rPr><w:delText>old</w:delText></w:r>
</w:del>
```

### Mistake: Duplicate w:id values

Every `<w:del>` and `<w:ins>` element needs its own unique ID. If you reuse IDs, Word will silently corrupt the revision history. Scan for the max existing ID and increment from there.
