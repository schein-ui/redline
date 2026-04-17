#!/usr/bin/env python3
"""
surgical_redline.py — Apply surgical tracked changes to a .docx file.

This is the reusable core of the redline skill's Word Mode. It takes an edit
list (word-level substitutions, paragraph-level replacements, paragraph
insertions) and produces a .docx with proper OOXML tracked changes that open
in Word with full Track Changes functionality (accept/reject per change,
filter by author, etc.).

USAGE (CLI with JSON edit list):

    python surgical_redline.py \\
        --in  /path/to/input.docx \\
        --out /path/to/output.docx \\
        --edits /path/to/edits.json \\
        [--author "Claude"] \\
        [--date "2026-04-16T12:00:00Z"]

USAGE (as a library, when Claude is writing a one-off driver):

    from surgical_redline import Redline
    r = Redline("/path/in.docx", author="Claude")
    r.replace("monthly", "quarterly")                             # word-level
    r.replace("$2.5M", "$3.1M")
    r.paragraph_replace(
        anchor="The go-to-market strategy relies on",             # any substring
        new_text="The go-to-market strategy combines ...",
        note="Restructured GTM from direct sales to hybrid model."
    )
    r.insert_paragraph_after(
        anchor="execution sequence matters",
        text="The next 90 days are decisive. ..."
    )
    r.save("/path/out.docx")
    print(r.report())                                             # summary of applied/failed edits

EDIT LIST JSON SCHEMA:

    {
      "edits": [
        {
          "type": "replace",
          "old": "monthly",
          "new": "quarterly"
        },
        {
          "type": "paragraph_replace",
          "anchor": "The go-to-market strategy relies on",
          "new": "The go-to-market strategy combines ...",
          "note": "Restructured GTM from direct sales to hybrid model."
        },
        {
          "type": "insert_after",
          "anchor": "execution sequence matters",
          "text": "The next 90 days are decisive. ..."
        },
        {
          "type": "insert_before",
          "anchor": "enterprise value creation",
          "text": "In closing, ..."
        }
      ]
    }

CHARACTER ENCODING — READ THIS FIRST:

Business documents are FULL of smart punctuation. If your edit's `old` text
fails to match, the #1 cause is character encoding. Watch for:

    \\xa0      non-breaking space   (looks like a regular space)
    \\u2019    right single quote   (looks like ')  — the smart apostrophe
    \\u2018    left single quote    (looks like `)
    \\u201C    left double quote    (looks like ")
    \\u201D    right double quote   (looks like ")
    \\u2013    en dash              (looks like -)
    \\u2014    em dash              (looks like --)
    \\u2026    ellipsis             (looks like ...)

When a replace fails, this script prints the surrounding paragraph text with
character codes so you can spot the mismatch. Copy the exact character from
the dump into your edit list.

LIMITATIONS:

- Paragraph-level notes are inserted as a tracked-change paragraph directly
  after the replacement, styled in italic brackets. Does not use Word's
  comments.xml. If you need margin comments, use the docx skill's comment.py
  as a post-step.
- Cannot insert or delete entire table rows via tracked changes (OOXML
  limitation — only cell content can be tracked).
- Does not handle move operations natively. Model a move as a deletion at
  the source and an insertion at the destination.
"""

import argparse
import copy
import json
import os
import shutil
import sys
import zipfile
from typing import Optional, List, Tuple

from lxml import etree

# ── Namespaces ─────────────────────────────────────────────────────────────

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def qn(tag: str) -> str:
    """Qualified name: 'w:t' -> '{http://.../2006/main}t'"""
    prefix, local = tag.split(":")
    ns = {"w": W, "w14": W14, "xml": XML_NS}
    return f"{{{ns[prefix]}}}{local}"


# ── Main class ─────────────────────────────────────────────────────────────


class Redline:
    """Apply surgical tracked changes to a .docx.

    All edits are queued against the in-memory document and written when
    save() is called. Each edit method returns True on success, False on
    failure, and records the outcome in self.report_lines.
    """

    def __init__(
        self,
        src_path: str,
        author: str = "Claude",
        date: str = "2026-01-01T00:00:00Z",
        work_dir: Optional[str] = None,
    ):
        self.src_path = src_path
        self.author = author
        self.date = date
        self.work_dir = work_dir or os.path.join("/tmp", "redline_work")
        self._next_id = 1000
        self.report_lines: List[str] = []
        self.applied = 0
        self.failed = 0

        self._unpack()
        self._load_xml()

    # ── Setup ──────────────────────────────────────────────────────────

    def _unpack(self):
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir)
        os.makedirs(self.work_dir)
        with zipfile.ZipFile(self.src_path, "r") as z:
            z.extractall(self.work_dir)

    def _load_xml(self):
        self.doc_path = os.path.join(self.work_dir, "word", "document.xml")
        parser = etree.XMLParser(remove_blank_text=False)
        self.tree = etree.parse(self.doc_path, parser)
        self.root = self.tree.getroot()
        self.body = self.root.find(qn("w:body"))

        # Find max existing w:id so we don't clash with any existing tracked changes
        max_id = 0
        for el in self.root.iter():
            id_attr = el.get(qn("w:id"))
            if id_attr and id_attr.isdigit():
                max_id = max(max_id, int(id_attr))
        self._next_id = max(max_id + 100, 1000)

    def _next(self) -> str:
        val = self._next_id
        self._next_id += 1
        return str(val)

    # ── XML building blocks ────────────────────────────────────────────

    def _make_run(self, text: str, rpr_template, tag: str = "w:t"):
        r = etree.Element(qn("w:r"))
        if rpr_template is not None:
            r.append(copy.deepcopy(rpr_template))
        t = etree.SubElement(r, qn(tag))
        t.text = text
        if text and (text[0] == " " or text[-1] == " " or "\xa0" in text):
            t.set(f"{{{XML_NS}}}space", "preserve")
        return r

    def _make_del(self, text: str, rpr_template):
        d = etree.Element(qn("w:del"))
        d.set(qn("w:id"), self._next())
        d.set(qn("w:author"), self.author)
        d.set(qn("w:date"), self.date)
        d.append(self._make_run(text, rpr_template, tag="w:delText"))
        return d

    def _make_ins(self, text: str, rpr_template):
        ins = etree.Element(qn("w:ins"))
        ins.set(qn("w:id"), self._next())
        ins.set(qn("w:author"), self.author)
        ins.set(qn("w:date"), self.date)
        ins.append(self._make_run(text, rpr_template, tag="w:t"))
        return ins

    def _wrap_ins(self, child_element):
        ins = etree.Element(qn("w:ins"))
        ins.set(qn("w:id"), self._next())
        ins.set(qn("w:author"), self.author)
        ins.set(qn("w:date"), self.date)
        ins.append(child_element)
        return ins

    # ── Paragraph helpers ──────────────────────────────────────────────

    @staticmethod
    def _para_text(para) -> str:
        texts = []
        for r in para.findall(f".//{qn('w:r')}"):
            for t in r.findall(qn("w:t")):
                if t.text:
                    texts.append(t.text)
        return "".join(texts)

    @staticmethod
    def _run_rpr(run):
        rpr = run.find(qn("w:rPr"))
        return copy.deepcopy(rpr) if rpr is not None else None

    def _find_para(self, substring: str):
        for p in self.body.findall(qn("w:p")):
            if substring in self._para_text(p):
                return p
        return None

    def _find_all_paras(self, substring: str):
        out = []
        for p in self.body.findall(qn("w:p")):
            if substring in self._para_text(p):
                out.append(p)
        return out

    def _diagnose_miss(self, needle: str) -> str:
        """When a lookup fails, build a diagnostic string. Checks several causes
        in order: (1) text exists inside an existing tracked change (w:ins/w:del)
        and should not be re-edited, (2) a near-match with different characters
        (smart punctuation, non-breaking spaces), (3) text genuinely absent."""
        # (1) Does the text exist inside an existing w:ins or w:del?
        for p in self.body.findall(qn("w:p")):
            for tracked in p.findall(f".//{qn('w:ins')}") + p.findall(f".//{qn('w:del')}"):
                tracked_text = "".join(
                    (t.text or "")
                    for t in tracked.findall(f".//{qn('w:t')}") + tracked.findall(f".//{qn('w:delText')}")
                )
                if needle in tracked_text:
                    author = tracked.get(qn("w:author"), "?")
                    kind = "w:ins" if tracked.tag == qn("w:ins") else "w:del"
                    return (
                        f"Text exists but is already inside a tracked change "
                        f"({kind} by {author!r}). Refusing to re-edit tracked content. "
                        f"If you need to modify another author's tracked change, do it manually."
                    )

        # (2) Prefix match — likely a character-encoding issue
        # Try with the needle as-is, then with whitespace/apostrophes normalized
        def _normalize(s: str) -> str:
            return (
                s.replace("\xa0", " ")
                .replace("\u2019", "'")
                .replace("\u2018", "'")
                .replace("\u201C", '"')
                .replace("\u201D", '"')
                .replace("\u2013", "-")
                .replace("\u2014", "--")
            )

        needle_norm = _normalize(needle)
        for length in (30, 20, 10, 6):
            if len(needle) < length:
                continue
            for p in self.body.findall(qn("w:p")):
                pt = self._para_text(p)
                pt_norm = _normalize(pt)
                # Try exact prefix match first
                prefix = needle[:length]
                if prefix in pt:
                    idx = pt.find(prefix)
                    window = pt[max(0, idx - 10) : idx + len(needle) + 10]
                    codes = " ".join(f"{c}({hex(ord(c))})" for c in window[:80])
                    return (
                        f"No exact match. Nearest paragraph containing '{prefix}':\n"
                        f"  Text:  {window!r}\n"
                        f"  Codes: {codes}\n"
                        f"  HINT:  Check for \\xa0 (non-breaking space), \\u2019 (smart '), "
                        f"\\u201C/\\u201D (smart \"), \\u2013/\\u2014 (en/em dash)."
                    )
                # Then try normalized — catches the case where your needle has a
                # regular space but the doc has \xa0 (or vice versa on apostrophes)
                prefix_norm = needle_norm[:length]
                if prefix_norm in pt_norm:
                    idx = pt_norm.find(prefix_norm)
                    window = pt[max(0, idx - 10) : idx + len(needle) + 10]
                    codes = " ".join(f"{c}({hex(ord(c))})" for c in window[:80])
                    return (
                        f"Near-match found but characters differ. Your needle: {needle[:60]!r}\n"
                        f"  Doc text:  {window!r}\n"
                        f"  Codes:     {codes}\n"
                        f"  HINT:  Smart punctuation or non-breaking space mismatch. "
                        f"Copy the exact characters from the codes above into your edit."
                    )

        # (3) Nothing found
        return (
            "No paragraph contains even a 10-char prefix of the target. "
            "Text may be absent, split across paragraph boundaries, or in a "
            "header/footer/textbox (not supported)."
        )

    # ── Public edit methods ────────────────────────────────────────────

    def replace(self, old: str, new: str, anchor: Optional[str] = None) -> bool:
        """Word-level replacement. Finds `old` in the doc and replaces with `new`
        as a tracked change.

        If `anchor` is provided, only searches paragraphs containing `anchor`
        (useful when the same phrase appears in multiple places and you only
        want to change one of them).
        """
        paras = self._find_all_paras(anchor) if anchor else self.body.findall(qn("w:p"))
        for p in paras:
            if old in self._para_text(p):
                ok = self._surgical_replace(p, old, new)
                if ok:
                    self.applied += 1
                    self.report_lines.append(
                        f"  ✓ replace: {old[:40]!r} → {new[:40]!r}"
                    )
                    return True
        self.failed += 1
        self.report_lines.append(f"  ✗ replace FAILED: {old[:60]!r}")
        self.report_lines.append("    " + self._diagnose_miss(old).replace("\n", "\n    "))
        return False

    def paragraph_replace(
        self, anchor: str, new_text: str, note: Optional[str] = None
    ) -> bool:
        """Paragraph-level replacement. Finds a paragraph containing `anchor`,
        wraps its entire content in w:del, inserts new_text in w:ins.

        If `note` is provided, inserts a second paragraph immediately after
        with the note text formatted as [Note: ...] — also as a tracked
        insertion. The note inherits paragraph formatting from the replaced
        paragraph.
        """
        p = self._find_para(anchor)
        if p is None:
            self.failed += 1
            self.report_lines.append(
                f"  ✗ paragraph_replace FAILED: anchor {anchor[:60]!r} not found"
            )
            self.report_lines.append(
                "    " + self._diagnose_miss(anchor).replace("\n", "\n    ")
            )
            return False

        # Collect runs
        runs = [child for child in p if child.tag == qn("w:r")]
        if not runs:
            self.failed += 1
            self.report_lines.append(
                f"  ✗ paragraph_replace FAILED: no runs in paragraph for {anchor[:60]!r}"
            )
            return False

        rpr = self._run_rpr(runs[0])
        old_text = "".join(
            t.text or ""
            for r in runs
            for t in r.findall(qn("w:t"))
        )

        first_pos = list(p).index(runs[0])
        for r in runs:
            p.remove(r)

        p.insert(first_pos, self._make_del(old_text, rpr))
        p.insert(first_pos + 1, self._make_ins(new_text, rpr))

        if note:
            self._insert_note_paragraph_after(p, note, rpr)

        self.applied += 1
        msg = f"  ✓ paragraph_replace: anchor={anchor[:40]!r}"
        if note:
            msg += " [+ note]"
        self.report_lines.append(msg)
        return True

    def insert_paragraph_after(self, anchor: str, text: str) -> bool:
        """Insert a new paragraph after the paragraph containing `anchor`.
        The new paragraph is marked as fully inserted (w:ins on paragraph
        break and on content run)."""
        ref = self._find_para(anchor)
        if ref is None:
            self.failed += 1
            self.report_lines.append(
                f"  ✗ insert_paragraph_after FAILED: anchor {anchor[:60]!r} not found"
            )
            return False
        self._insert_new_paragraph(ref, text, position="after")
        self.applied += 1
        self.report_lines.append(
            f"  ✓ insert_paragraph_after: anchor={anchor[:40]!r}"
        )
        return True

    def insert_paragraph_before(self, anchor: str, text: str) -> bool:
        """Insert a new paragraph before the paragraph containing `anchor`."""
        ref = self._find_para(anchor)
        if ref is None:
            self.failed += 1
            self.report_lines.append(
                f"  ✗ insert_paragraph_before FAILED: anchor {anchor[:60]!r} not found"
            )
            return False
        self._insert_new_paragraph(ref, text, position="before")
        self.applied += 1
        self.report_lines.append(
            f"  ✓ insert_paragraph_before: anchor={anchor[:40]!r}"
        )
        return True

    # ── Core surgical logic ────────────────────────────────────────────

    def _surgical_replace(self, para, old_text: str, new_text: str) -> bool:
        """Split the paragraph's runs at exact char boundaries, wrap only the
        matched region in w:del/w:ins, preserve everything else verbatim."""
        runs = []
        for child in list(para):
            if child.tag == qn("w:r"):
                t_el = child.find(qn("w:t"))
                runs.append((child, t_el.text if (t_el is not None and t_el.text) else ""))

        full_text = ""
        char_map: List[Tuple[int, int]] = []
        for ri, (_, txt) in enumerate(runs):
            for ci, ch in enumerate(txt):
                char_map.append((ri, ci))
                full_text += ch

        pos = full_text.find(old_text)
        if pos == -1:
            return False

        end_pos = pos + len(old_text)
        start_ri, start_off = char_map[pos]
        end_ri, end_off = char_map[end_pos - 1]

        first_run = runs[start_ri][0]
        start_rpr = self._run_rpr(first_run)
        end_rpr = self._run_rpr(runs[end_ri][0])

        prefix_text = runs[start_ri][1][:start_off]
        suffix_text = runs[end_ri][1][end_off + 1:]

        new_elements = []
        if prefix_text:
            new_elements.append(self._make_run(prefix_text, start_rpr))
        new_elements.append(self._make_del(old_text, start_rpr))
        if new_text:
            new_elements.append(self._make_ins(new_text, start_rpr))
        if suffix_text:
            new_elements.append(self._make_run(suffix_text, end_rpr))

        insert_pos = list(para).index(runs[start_ri][0])
        for ri in range(start_ri, end_ri + 1):
            para.remove(runs[ri][0])
        for i, el in enumerate(new_elements):
            para.insert(insert_pos + i, el)

        return True

    def _insert_new_paragraph(self, ref_para, text: str, position: str):
        """Insert a new paragraph with tracked-insertion markup before or after
        ref_para."""
        ref_rpr = None
        for r in ref_para.findall(f".//{qn('w:r')}"):
            ref_rpr = self._run_rpr(r)
            if ref_rpr is not None:
                break

        new_p = self._build_inserted_paragraph(text, ref_para, ref_rpr)

        idx = list(self.body).index(ref_para)
        self.body.insert(idx + (1 if position == "after" else 0), new_p)

    def _insert_note_paragraph_after(self, ref_para, note_text: str, rpr):
        """For paragraph_replace: insert an italic-bracketed note paragraph
        directly after the replaced paragraph, as a tracked insertion."""
        italic_rpr = copy.deepcopy(rpr) if rpr is not None else etree.Element(qn("w:rPr"))
        # Add italic if not already present
        if italic_rpr.find(qn("w:i")) is None:
            etree.SubElement(italic_rpr, qn("w:i"))

        note_formatted = f"[Note: {note_text}]"
        new_p = self._build_inserted_paragraph(note_formatted, ref_para, italic_rpr)

        idx = list(self.body).index(ref_para)
        self.body.insert(idx + 1, new_p)

    def _build_inserted_paragraph(self, text: str, ref_para, ref_rpr):
        """Build a <w:p> with tracked-insertion markup on both the paragraph
        break and the content run."""
        new_p = etree.Element(qn("w:p"))

        ref_ppr = ref_para.find(qn("w:pPr"))
        if ref_ppr is not None:
            new_ppr = copy.deepcopy(ref_ppr)
        else:
            new_ppr = etree.Element(qn("w:pPr"))

        ppr_rpr = new_ppr.find(qn("w:rPr"))
        if ppr_rpr is None:
            ppr_rpr = etree.SubElement(new_ppr, qn("w:rPr"))
        ins_mark = etree.SubElement(ppr_rpr, qn("w:ins"))
        ins_mark.set(qn("w:id"), self._next())
        ins_mark.set(qn("w:author"), self.author)
        ins_mark.set(qn("w:date"), self.date)

        new_p.append(new_ppr)

        run = self._make_run(text, ref_rpr)
        new_p.append(self._wrap_ins(run))
        return new_p

    # ── Save ───────────────────────────────────────────────────────────

    def _enable_track_revisions(self):
        settings_path = os.path.join(self.work_dir, "word", "settings.xml")
        if not os.path.exists(settings_path):
            return
        parser = etree.XMLParser(remove_blank_text=False)
        stree = etree.parse(settings_path, parser)
        sroot = stree.getroot()
        if sroot.find(qn("w:trackRevisions")) is None:
            tr = etree.Element(qn("w:trackRevisions"))
            # Insert near top (position 1 to stay after any view/zoom settings)
            sroot.insert(min(1, len(sroot)), tr)
        stree.write(
            settings_path, xml_declaration=True, encoding="UTF-8", standalone=True
        )

    def save(self, out_path: str):
        self.tree.write(
            self.doc_path,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        )
        self._enable_track_revisions()

        if os.path.exists(out_path):
            os.remove(out_path)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for dirpath, _, filenames in os.walk(self.work_dir):
                for fn in filenames:
                    full = os.path.join(dirpath, fn)
                    arc = os.path.relpath(full, self.work_dir)
                    zout.write(full, arc)

    def report(self) -> str:
        lines = [
            f"Redline report",
            f"  Source: {self.src_path}",
            f"  Author: {self.author}",
            f"  Applied: {self.applied}",
            f"  Failed:  {self.failed}",
            "",
        ]
        lines.extend(self.report_lines)
        return "\n".join(lines)


# ── CLI driver ─────────────────────────────────────────────────────────────


def _apply_edit_list(r: Redline, edits: list):
    """Dispatch a list of edit dicts to the appropriate Redline method."""
    for i, e in enumerate(edits, 1):
        etype = e.get("type")
        if etype == "replace":
            r.replace(e["old"], e["new"], anchor=e.get("anchor"))
        elif etype == "paragraph_replace":
            r.paragraph_replace(e["anchor"], e["new"], note=e.get("note"))
        elif etype == "insert_after":
            r.insert_paragraph_after(e["anchor"], e["text"])
        elif etype == "insert_before":
            r.insert_paragraph_before(e["anchor"], e["text"])
        else:
            r.report_lines.append(f"  ? edit #{i}: unknown type {etype!r} — skipped")
            r.failed += 1


def main():
    ap = argparse.ArgumentParser(description="Apply surgical tracked changes to a .docx")
    ap.add_argument("--in", dest="src", required=True, help="Input .docx path")
    ap.add_argument("--out", dest="dst", required=True, help="Output .docx path")
    ap.add_argument("--edits", required=True, help="Edit list JSON file")
    ap.add_argument("--author", default="Claude", help='Author name (default: "Claude")')
    ap.add_argument("--date", default="2026-01-01T00:00:00Z", help="ISO 8601 timestamp")
    args = ap.parse_args()

    with open(args.edits, "r", encoding="utf-8") as f:
        spec = json.load(f)

    r = Redline(args.src, author=args.author, date=args.date)
    _apply_edit_list(r, spec.get("edits", []))
    r.save(args.dst)
    print(r.report())

    if r.failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
