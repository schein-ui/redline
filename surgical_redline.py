#!/usr/bin/env python3
"""
Surgical redline script for HungerRush Strategic Pivot Memo.
Produces proper tracked changes by splitting runs at exact word boundaries.
"""

import zipfile
import shutil
import os
import re
import copy
from lxml import etree

# ── Config ──────────────────────────────────────────────────────────────────
SRC = "/Users/jeremyschein/Downloads/CLEAN_HungerRush_Strategic_Pivot_Memo_v.2_04.04.2026.docx"
DST = "/Users/jeremyschein/Downloads/CLEAN_HungerRush_Memo_v2_REDLINE_JS.docx"
TMP = "/tmp/redline_work"
AUTHOR = "JS Review"
DATE = "2026-04-04T21:00:00Z"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
XML_NS = "http://www.w3.org/XML/1998/namespace"

NSMAP = {
    'w': W,
    'w14': W14,
}

# Global w:id counter
_next_id = 1000

def next_id():
    global _next_id
    _next_id += 1
    return str(_next_id - 1)


# ── Helpers ─────────────────────────────────────────────────────────────────

def qn(tag):
    """Qualified name: 'w:t' -> '{http://...}t'"""
    prefix, local = tag.split(':')
    ns = {'w': W, 'w14': W14, 'xml': XML_NS}
    return f'{{{ns[prefix]}}}{local}'


def get_para_text(para):
    """Concatenate all w:t text in a paragraph."""
    texts = []
    for r in para.findall(f'.//{qn("w:r")}'):
        for t in r.findall(qn('w:t')):
            if t.text:
                texts.append(t.text)
    return ''.join(texts)


def get_run_rpr(run):
    """Return a deep copy of the run's w:rPr, or None."""
    rpr = run.find(qn('w:rPr'))
    if rpr is not None:
        return copy.deepcopy(rpr)
    return None


def make_t(text, tag='w:t'):
    """Create a w:t or w:delText element with proper xml:space."""
    el = etree.SubElement(etree.Element('dummy'), qn(tag))
    el.text = text
    if text and (text[0] == ' ' or text[-1] == ' '):
        el.set(f'{{{XML_NS}}}space', 'preserve')
    return el


def make_run_with_text(text, rpr_template, tag='w:t'):
    """Create a w:r element with optional rPr and a text element."""
    r = etree.Element(qn('w:r'))
    if rpr_template is not None:
        r.append(copy.deepcopy(rpr_template))
    t = etree.SubElement(r, qn(tag))
    t.text = text
    if text and (text[0] == ' ' or text[-1] == ' '):
        t.set(f'{{{XML_NS}}}space', 'preserve')
    return r


def make_del(text, rpr_template):
    """Create a w:del element containing a w:r with w:delText."""
    d = etree.Element(qn('w:del'))
    d.set(qn('w:id'), next_id())
    d.set(qn('w:author'), AUTHOR)
    d.set(qn('w:date'), DATE)
    r = make_run_with_text(text, rpr_template, tag='w:delText')
    d.append(r)
    return d


def make_ins(text, rpr_template):
    """Create a w:ins element containing a w:r with w:t."""
    ins = etree.Element(qn('w:ins'))
    ins.set(qn('w:id'), next_id())
    ins.set(qn('w:author'), AUTHOR)
    ins.set(qn('w:date'), DATE)
    r = make_run_with_text(text, rpr_template, tag='w:t')
    ins.append(r)
    return ins


def make_ins_element(child_element):
    """Wrap any element in a w:ins."""
    ins = etree.Element(qn('w:ins'))
    ins.set(qn('w:id'), next_id())
    ins.set(qn('w:author'), AUTHOR)
    ins.set(qn('w:date'), DATE)
    ins.append(child_element)
    return ins


def find_para_containing(body, text, start_hint=None):
    """Find a paragraph whose concatenated text contains `text`."""
    paras = body.findall(qn('w:p'))
    for i, p in enumerate(paras):
        if start_hint is not None and i < start_hint:
            continue
        pt = get_para_text(p)
        if text in pt:
            return p, i
    return None, -1


def find_all_paras_containing(body, text):
    """Find all paragraphs whose concatenated text contains `text`."""
    results = []
    paras = body.findall(qn('w:p'))
    for i, p in enumerate(paras):
        pt = get_para_text(p)
        if text in pt:
            results.append((p, i))
    return results


# ── Core surgical replacement ──────────────────────────────────────────────

def surgical_replace_in_para(para, old_text, new_text):
    """
    Find `old_text` within the paragraph's concatenated run text,
    split the run(s) at exact boundaries, and wrap only the changed
    portion in w:del/w:ins. Everything else stays in plain runs.
    """
    # 1. Collect all runs and their text
    runs = []
    for child in list(para):
        tag = child.tag
        if tag == qn('w:r'):
            t_el = child.find(qn('w:t'))
            if t_el is not None and t_el.text:
                runs.append((child, t_el.text))
            else:
                runs.append((child, ''))
        # Skip non-run elements (pPr, bookmarks, etc.)

    # 2. Build concatenated text and char-to-run mapping
    full_text = ''
    char_map = []  # (run_index, offset_within_run) for each char
    for ri, (run, txt) in enumerate(runs):
        for ci, ch in enumerate(txt):
            char_map.append((ri, ci))
            full_text += ch

    # 3. Find the old_text in the concatenated text
    pos = full_text.find(old_text)
    if pos == -1:
        print(f"  WARNING: Could not find '{old_text[:60]}...' in paragraph text")
        print(f"  Para text: '{full_text[:200]}'")
        return False

    end_pos = pos + len(old_text)

    # 4. Determine which runs are affected
    start_run_idx, start_offset = char_map[pos]
    end_run_idx, end_offset = char_map[end_pos - 1]

    # 5. Build replacement elements
    # We need to:
    #   - Keep prefix of start_run (before old_text starts)
    #   - w:del with old_text
    #   - w:ins with new_text
    #   - Keep suffix of end_run (after old_text ends)
    #   - Remove any runs fully consumed between start and end

    # Get rPr from the first affected run
    first_run = runs[start_run_idx][0]
    rpr = get_run_rpr(first_run)

    # Calculate prefix and suffix text
    start_run_text = runs[start_run_idx][1]
    end_run_text = runs[end_run_idx][1]

    prefix_text = start_run_text[:start_offset]
    suffix_text = end_run_text[end_offset + 1:]

    # 6. Build new elements to insert
    new_elements = []

    if prefix_text:
        new_elements.append(make_run_with_text(prefix_text, rpr))

    new_elements.append(make_del(old_text, rpr))

    if new_text:  # Could be empty for pure deletions
        new_elements.append(make_ins(new_text, rpr))

    if suffix_text:
        # Use rPr from the end run
        end_rpr = get_run_rpr(runs[end_run_idx][0])
        new_elements.append(make_run_with_text(suffix_text, end_rpr))

    # 7. Find the position of the first affected run in the paragraph
    first_run_el = runs[start_run_idx][0]
    insert_pos = list(para).index(first_run_el)

    # 8. Remove all affected runs
    for ri in range(start_run_idx, end_run_idx + 1):
        para.remove(runs[ri][0])

    # 9. Insert new elements at the correct position
    for i, el in enumerate(new_elements):
        para.insert(insert_pos + i, el)

    return True


def paragraph_level_replace(para, new_text):
    """
    For paragraph-level replacements: wrap all existing content runs in w:del,
    then add new content in w:ins. Preserve formatting from first run.
    """
    # Collect all runs
    runs = [child for child in para if child.tag == qn('w:r')]
    if not runs:
        return False

    # Get rPr from first run
    rpr = get_run_rpr(runs[0])

    # Get full old text
    old_text = ''
    for r in runs:
        t = r.find(qn('w:t'))
        if t is not None and t.text:
            old_text += t.text

    # Find position of first run
    first_pos = list(para).index(runs[0])

    # Remove all runs
    for r in runs:
        para.remove(r)

    # Insert w:del with old text
    del_el = make_del(old_text, rpr)
    para.insert(first_pos, del_el)

    # Insert w:ins with new text
    ins_el = make_ins(new_text, rpr)
    para.insert(first_pos + 1, ins_el)

    return True


def insert_new_paragraph_after(body, ref_para, text, ref_rpr=None):
    """Insert a new paragraph after ref_para, marked as inserted."""
    paras = list(body)
    pos = list(body).index(ref_para)

    # Create paragraph
    new_p = etree.Element(qn('w:p'))

    # Copy pPr from ref_para if exists, and add insertion mark
    ref_ppr = ref_para.find(qn('w:pPr'))
    if ref_ppr is not None:
        new_ppr = copy.deepcopy(ref_ppr)
    else:
        new_ppr = etree.SubElement(new_p, qn('w:pPr'))

    # Add rPr with ins inside pPr to mark paragraph break as inserted
    ppr_rpr = new_ppr.find(qn('w:rPr'))
    if ppr_rpr is None:
        ppr_rpr = etree.SubElement(new_ppr, qn('w:rPr'))
    ins_mark = etree.SubElement(ppr_rpr, qn('w:ins'))
    ins_mark.set(qn('w:id'), next_id())
    ins_mark.set(qn('w:author'), AUTHOR)
    ins_mark.set(qn('w:date'), DATE)

    new_p.insert(0, new_ppr)

    # Create the run with text, wrapped in w:ins
    if ref_rpr is None:
        # Try to get from ref_para's first run
        for r in ref_para.findall(f'.//{qn("w:r")}'):
            ref_rpr = get_run_rpr(r)
            if ref_rpr is not None:
                break

    r = make_run_with_text(text, ref_rpr)
    ins_el = make_ins_element(r)
    new_p.append(ins_el)

    # Insert after ref_para
    body.insert(pos + 1, new_p)
    return new_p


def insert_new_paragraph_before(body, ref_para, text, ref_rpr=None):
    """Insert a new paragraph before ref_para, marked as inserted."""
    pos = list(body).index(ref_para)

    new_p = etree.Element(qn('w:p'))

    ref_ppr = ref_para.find(qn('w:pPr'))
    if ref_ppr is not None:
        new_ppr = copy.deepcopy(ref_ppr)
    else:
        new_ppr = etree.SubElement(new_p, qn('w:pPr'))

    ppr_rpr = new_ppr.find(qn('w:rPr'))
    if ppr_rpr is None:
        ppr_rpr = etree.SubElement(new_ppr, qn('w:rPr'))
    ins_mark = etree.SubElement(ppr_rpr, qn('w:ins'))
    ins_mark.set(qn('w:id'), next_id())
    ins_mark.set(qn('w:author'), AUTHOR)
    ins_mark.set(qn('w:date'), DATE)

    new_p.insert(0, new_ppr)

    if ref_rpr is None:
        for r in ref_para.findall(f'.//{qn("w:r")}'):
            ref_rpr = get_run_rpr(r)
            if ref_rpr is not None:
                break

    r = make_run_with_text(text, ref_rpr)
    ins_el = make_ins_element(r)
    new_p.append(ins_el)

    body.insert(pos, new_p)
    return new_p


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    # 1. Unzip
    if os.path.exists(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)

    with zipfile.ZipFile(SRC, 'r') as z:
        z.extractall(TMP)

    # 2. Parse document.xml with lxml (preserves namespaces better)
    doc_path = os.path.join(TMP, 'word', 'document.xml')
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(doc_path, parser)
    root = tree.getroot()
    body = root.find(qn('w:body'))

    # ── Apply changes ───────────────────────────────────────────────────

    # Change 1a: "cash savings" → "net cash savings" in P12
    # Note: original uses \xa0 (non-breaking space) around this text
    print("Change 1a: cash savings → net cash savings")
    p, _ = find_para_containing(body, "The Company has communicated")
    if p is not None:
        surgical_replace_in_para(p, "cash\xa0savings", "net cash savings")

    # Change 1b: "The company needs" → "The Company must" in same para
    # Note: after change 1a, need to re-find the para
    print("Change 1b: The company needs → The Company must")
    p, _ = find_para_containing(body, "The Company has communicated")
    if p is not None:
        surgical_replace_in_para(p, "The company needs", "The Company must")

    # Change 1c: "long term plan to allow for ongoing covenant compliance" → ...
    print("Change 1c: long term plan...")
    p, _ = find_para_containing(body, "The Company has communicated")
    if p is not None:
        surgical_replace_in_para(
            p,
            "long term plan to allow for ongoing covenant compliance",
            "long-term plan that creates ongoing covenant compliance and eliminates Going Concern risk"
        )

    # Change 1d: "The self-critique findings have revealed" → "Internal analysis has revealed"
    print("Change 1d: self-critique findings")
    p, _ = find_para_containing(body, "The Company has communicated")
    if p is not None:
        surgical_replace_in_para(p, "The self-critique findings have revealed", "Internal analysis has revealed")

    # Change 1e: "annual cash drain" → "annual cash drain that must be addressed..."
    # The original text ends with "annual cash drain" possibly followed by more text
    # Need to check exact text
    print("Change 1e: annual cash drain completion")
    p, _ = find_para_containing(body, "The Company has communicated")
    if p is not None:
        pt = get_para_text(p)
        # Check if there's already text after "annual cash drain"
        idx = pt.find("annual cash drain")
        if idx >= 0:
            after = pt[idx + len("annual cash drain"):]
            # We want to replace just "annual cash drain" with the expanded version
            # But only if the sentence doesn't already continue
            if after.strip() == '' or after.strip()[0:1] in ('', '.'):
                surgical_replace_in_para(
                    p,
                    "annual cash drain",
                    "annual cash drain that must be addressed through both cost reduction and revenue growth."
                )
            else:
                # Text continues — just do the replacement at end
                surgical_replace_in_para(
                    p,
                    "annual cash drain",
                    "annual cash drain that must be addressed through both cost reduction and revenue growth."
                )

    # Change 2a: strangler-fig modernization in P14
    print("Change 2a: strangler-fig modernization")
    p, _ = find_para_containing(body, "a strangler-fig modernization of the POS platform")
    if p is not None:
        surgical_replace_in_para(
            p,
            "a strangler-fig modernization of the POS platform",
            "a strangler fig modernization, a phased, module-by-module modernization of the POS platform (replacing legacy components incrementally while maintaining the existing system)"
        )

    # Change 2b: "sales and marketing" → "Sales & Marketing" in same para
    print("Change 2b: sales and marketing → Sales & Marketing")
    p, _ = find_para_containing(body, "strangler fig modernization")
    if p is not None:
        surgical_replace_in_para(p, "sales and marketing", "Sales & Marketing")

    # Change 3a: Bottom Line - "The strategy is..." → "This strategy is..."
    print("Change 3a: The strategy → This strategy")
    p, _ = find_para_containing(body, "The strategy is financially viable")
    if p is not None:
        surgical_replace_in_para(
            p,
            "The strategy is financially viable, operationally demanding, and existentially necessary",
            "This strategy is financially viable and operationally demanding"
        )

    # Change 3b: "under-invested" → "under-resourced, and the window..."
    print("Change 3b: under-invested → under-resourced...")
    p, _ = find_para_containing(body, "under-invested")
    if p is not None:
        # Need to see exact context. The text ends with "under-invested" possibly followed by space
        pt = get_para_text(p)
        # Find what comes after "under-invested"
        idx = pt.find("under-invested")
        if idx >= 0:
            after_text = pt[idx + len("under-invested"):]
            # Replace "under-invested" plus trailing content with new text
            old = "under-invested"
            # Check if there's trailing content to preserve or replace
            if after_text.strip():
                old = "under-invested" + after_text  # replace everything after too
            surgical_replace_in_para(
                p,
                old,
                "under-resourced, and the window for competitive differentiation in AI-powered ordering closes permanently."
            )

    # Change 4: "ineffecient" → "inefficient"
    print("Change 4: ineffecient → inefficient")
    p, _ = find_para_containing(body, "ineffecient")
    if p is not None:
        surgical_replace_in_para(p, "ineffecient", "inefficient")

    # Change 5: "the Lender Group" (missing period) in P38
    print("Change 5: Lender Group + period")
    p, _ = find_para_containing(body, "The Company must deliver a $5M cash savings plan to the Lender Group")
    if p is not None:
        pt = get_para_text(p)
        # Check if it already ends with a period
        if pt.rstrip().endswith("the Lender Group"):
            surgical_replace_in_para(p, "the Lender Group", "the Lender Group.")

    # Change 6: hunt elephants
    # Note: "can't" uses smart apostrophe \u2019
    print("Change 6: hunt elephants")
    p, _ = find_para_containing(body, "hunt elephants")
    if p is not None:
        surgical_replace_in_para(
            p,
            "but ONLY if economics are clear.  We can\u2019t hunt elephants.",
            "but ONLY if unit economics are clear. Large, complex opportunities will be evaluated only if they can accept the current product state and can close with a clear line of sight within 60 days."
        )

    # Change 7 & 8: "Driving principles:" → "Driving Principles:" and "Driving Principle:" → "Driving Principles:"
    print("Change 7/8: Driving principles/Principle → Driving Principles:")
    for variant in ["Driving principles:", "Driving principles: ", "Driving Principle:", "Driving Principle: "]:
        matches = find_all_paras_containing(body, variant)
        for p, idx in matches:
            pt = get_para_text(p)
            # Find exact match
            if variant in pt:
                new_variant = variant.replace("principles:", "Principles:").replace("Principle:", "Principles:")
                surgical_replace_in_para(p, variant, new_variant)

    # Change 9: "execution sequence matters" → "execution sequence matters."
    print("Change 9: execution sequence matters + period")
    p, _ = find_para_containing(body, "execution sequence matters")
    if p is not None:
        pt = get_para_text(p)
        if "execution sequence matters." not in pt:
            surgical_replace_in_para(p, "execution sequence matters", "execution sequence matters.")

    # Change 10: "milestones must be explicit" → "milestones must be explicit."
    print("Change 10: milestones must be explicit + period")
    p, _ = find_para_containing(body, "milestones must be explicit")
    if p is not None:
        pt = get_para_text(p)
        if "milestones must be explicit." not in pt:
            surgical_replace_in_para(p, "milestones must be explicit", "milestones must be explicit.")

    # Change 11: "The is the strongest" → "This is the strongest"
    print("Change 11: The is → This is")
    p, _ = find_para_containing(body, "The is the strongest")
    if p is not None:
        surgical_replace_in_para(p, "The is the strongest", "This is the strongest")
    else:
        # Might be split across runs: "The " + "is the strongest"
        # Try looking for it more carefully
        p, _ = find_para_containing(body, "is the strongest")
        if p is not None:
            pt = get_para_text(p)
            if "The is the strongest" in pt:
                surgical_replace_in_para(p, "The is the strongest", "This is the strongest")

    # Change 12: extra spaces "sales team  to 35.  Also"
    print("Change 12: fix double spaces")
    p, _ = find_para_containing(body, "sales team")
    if p is not None:
        pt = get_para_text(p)
        if "sales team  to 35." in pt:
            surgical_replace_in_para(p, "sales team  to 35.  Also", "sales team to 35. Also")
        elif "sales team to 35." in pt:
            # Spaces might be in different form
            pass

    # Change 13: "before any ramping efforts" → "before any ramping efforts."
    print("Change 13: ramping efforts + period")
    p, _ = find_para_containing(body, "before any ramping efforts")
    if p is not None:
        pt = get_para_text(p)
        if "before any ramping efforts." not in pt:
            surgical_replace_in_para(p, "before any ramping efforts", "before any ramping efforts.")

    # Change 14: "the Goldman timeline" → "the Lender Group timeline"
    print("Change 14: Goldman timeline")
    p, _ = find_para_containing(body, "the Goldman timeline")
    if p is not None:
        surgical_replace_in_para(p, "the Goldman timeline", "the Lender Group timeline")

    # Change 15: "Goldman interim update" → "Lender Group interim update"
    print("Change 15: Goldman interim update")
    p, _ = find_para_containing(body, "Goldman interim update")
    if p is not None:
        surgical_replace_in_para(p, "Goldman interim update", "Lender Group interim update")

    # Change 16: "(FY26E) per Goldman Lender Deck" → "(FY 2026 estimated) per Lender Group deck"
    print("Change 16: FY26E Goldman")
    # The text might be "(FY26E)" but from the para dump it showed "2,000+ locations (FY26E) per Goldman Lender Deck"
    p, _ = find_para_containing(body, "per Goldman Lender Deck")
    if p is not None:
        surgical_replace_in_para(p, "(FY26E) per Goldman Lender Deck", "(FY 2026 estimated) per Lender Group deck")
    else:
        # Try alternate form
        p, _ = find_para_containing(body, "Goldman Lender Deck")
        if p is not None:
            pt = get_para_text(p)
            print(f"  Found para with Goldman Lender Deck: {pt[:200]}")

    # Change 17: "Goldman covenant compliance" → "Lender Group covenant compliance"
    print("Change 17: Goldman covenant")
    p, _ = find_para_containing(body, "Goldman covenant compliance")
    if p is not None:
        surgical_replace_in_para(p, "Goldman covenant compliance", "Lender Group covenant compliance")

    # Change 18: "8. Lender Compliance" → "9. Lender Compliance"
    print("Change 18: 8. Lender → 9. Lender")
    p, _ = find_para_containing(body, "8. Lender Compliance")
    if p is not None:
        surgical_replace_in_para(p, "8. Lender Compliance", "9. Lender Compliance")

    # Change 19: "8. Governance" → "10. Governance"
    print("Change 19: 8. Governance → 10. Governance")
    p, _ = find_para_containing(body, "8. Governance")
    if p is not None:
        surgical_replace_in_para(p, "8. Governance", "10. Governance")

    # Change 20: "Corsair-led lender communication" → "Corsair-led Lender Group communication"
    print("Change 20: Corsair-led lender")
    p, _ = find_para_containing(body, "Corsair-led lender communication")
    if p is not None:
        surgical_replace_in_para(p, "Corsair-led lender communication", "Corsair-led Lender Group communication")

    # Change 21: "seven-pillar" → "eight-pillar"
    print("Change 21: seven-pillar → eight-pillar")
    p, _ = find_para_containing(body, "seven-pillar")
    if p is not None:
        surgical_replace_in_para(p, "seven-pillar", "eight-pillar")

    # Change 22: "quickly.." → "quickly."
    print("Change 22: quickly.. → quickly.")
    # Need to find which paragraph has this
    matches = find_all_paras_containing(body, "quickly..")
    for p, idx in matches:
        surgical_replace_in_para(p, "quickly..", "quickly.")

    # Change 23: "creation—" → "creation —" (em-dash spacing)
    print("Change 23: creation— → creation —")
    p, _ = find_para_containing(body, "creation\u2014")
    if p is not None:
        surgical_replace_in_para(p, "creation\u2014", "creation \u2014")
    else:
        # Try the plain dash form
        p, _ = find_para_containing(body, "creation—")
        if p is not None:
            surgical_replace_in_para(p, "creation—", "creation —")

    # Change 24 (paragraph-level): NPS statement
    print("Change 24: NPS paragraph replacement")
    p, _ = find_para_containing(body, "NPS will drop 15")
    if p is not None:
        paragraph_level_replace(
            p,
            "We anticipate a temporary NPS impact of up to 15\u201325 points during the transition period, with potential incremental churn of 2\u20135 percentage points. The retention program ($150\u2013200K), self-serve infrastructure investment, and phased timeline are designed to mitigate this impact and recover NPS to within 10 points of current levels by Q4 2026."
        )

    # Change 25 (paragraph-level): P&T triple-superlative
    print("Change 25: P&T triple-superlative replacement")
    p, _ = find_para_containing(body, "strategically indefensible")
    if p is not None:
        paragraph_level_replace(
            p,
            "Cutting P&T headcount beyond the 5\u20137% optimization threshold would delay POS modernization by an estimated 6\u201312 months, push the Menufy product roadmap into 2028, and put approximately $[X]M in projected new revenue at risk. The short-term savings (~$1\u20132M) would be more than offset by delayed value creation and increased competitive exposure."
        )

    # Change 26: Enterprise value vague
    print("Change 26: enterprise value vague")
    p, _ = find_para_containing(body, "at the expense of generating substantially greater enterprise value")
    if p is not None:
        surgical_replace_in_para(
            p,
            "at the expense of generating substantially greater enterprise value",
            "at the expense of $[X\u2013Y]M in enterprise value \u2014 a ratio of $1 saved for every $[N] lost."
        )

    # Change 27 (new paragraph): Insert after validation gate
    print("Change 27: Insert FLAG paragraph after validation gate")
    p, _ = find_para_containing(body, "Cost Phase 1")
    if p is not None:
        insert_new_paragraph_after(
            body, p,
            "[FLAG FOR FINN/FERNANDO: The $1.2M Phase 1 figure above does not match the ~$0.5M Phase 1 savings target in the Execution Roadmap (Section 7). Please reconcile.]"
        )

    # Change 28 (new paragraph): Insert before closing paragraph
    print("Change 28: Insert 90-day paragraph before closing")
    p, _ = find_para_containing(body, "enterprise value creation")
    if p is not None:
        insert_new_paragraph_before(
            body, p,
            "The next 90 days are decisive. In Month 1, we execute the POS S&M restructuring, engage the Menufy Sales Director search, and deploy the customer retention playbook for the top 50 accounts. By Month 3, the cost savings will be visible, the Menufy team will be building, and the lender narrative can have tangible progress behind it."
        )

    # ── Fix Goldman → Lender Group in governance table ──────────────────
    print("Change extra: Monthly Goldman reporting → Monthly Lender Group reporting")
    p, _ = find_para_containing(body, "Monthly Goldman reporting")
    if p is not None:
        surgical_replace_in_para(p, "Monthly Goldman reporting", "Monthly Lender Group reporting")

    # ── Write modified XML ──────────────────────────────────────────────
    # Write document.xml
    tree.write(doc_path, xml_declaration=True, encoding='UTF-8', standalone=True)

    # ── Add trackRevisions to settings.xml ──────────────────────────────
    settings_path = os.path.join(TMP, 'word', 'settings.xml')
    stree = etree.parse(settings_path, parser)
    sroot = stree.getroot()

    # Check if trackRevisions already exists
    existing = sroot.find(qn('w:trackRevisions'))
    if existing is None:
        # Add it after the first element
        tr = etree.SubElement(sroot, qn('w:trackRevisions'))
        # Move it to be near the beginning (after first child)
        children = list(sroot)
        if len(children) > 1:
            sroot.remove(tr)
            sroot.insert(1, tr)

    stree.write(settings_path, xml_declaration=True, encoding='UTF-8', standalone=True)

    # ── Rezip as docx ──────────────────────────────────────────────────
    if os.path.exists(DST):
        os.remove(DST)

    with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
        for dirpath, dirnames, filenames in os.walk(TMP):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                arcname = os.path.relpath(full, TMP)
                zout.write(full, arcname)

    print(f"\nDone! Output: {DST}")
    print(f"File size: {os.path.getsize(DST)} bytes")


if __name__ == '__main__':
    main()
