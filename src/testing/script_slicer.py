"""
script_slicer.py — Extracts verbatim script excerpts from a source file
using start_marker and end_marker phrases produced by the Section Mapper (Pass 1).

The model outputs short, unique phrases pointing to section boundaries.
This script does the actual text extraction, which is a code job — not a
model job. This eliminates the verbatim-copying problem that caused
section collapse in the original approach.

Usage:
    from src.testing.script_slicer import slice_sections
    sections = slice_sections(xml_output, script_path)
"""

import re


def _normalize(text: str) -> str:
    """Collapse all whitespace (newlines, tabs, multiple spaces) into a single space."""
    return re.sub(r'\s+', ' ', text).strip()


def _find_marker_position(script_normalized: str, marker: str) -> int:
    """
    Find the character position of a marker in the normalized script.
    Raises ValueError with a helpful message if not found.
    """
    marker_normalized = _normalize(marker)
    pos = script_normalized.find(marker_normalized)
    if pos == -1:
        raise ValueError(
            f"Marker not found in script:\n  '{marker_normalized}'\n\n"
            f"Check that the model copied the phrase verbatim from the source text."
        )
    return pos


def slice_sections(pass1_xml: str, script_path: str) -> list[dict]:
    """
    Parse Pass 1 XML output and extract real script excerpts for each section.

    Args:
        pass1_xml:   The raw XML string output from the Section Mapper (Pass 1).
        script_path: Absolute path to the source script file.

    Returns:
        A list of section dicts, each with:
          - id, title, narrative_territory, contains_chapter_break,
            suggested_beat_count, start_marker, end_marker, script_excerpt
    """
    # Load and normalize the full script once
    with open(script_path, 'r', encoding='utf-8') as f:
        script_raw = f.read()
    script_normalized = _normalize(script_raw)

    # Parse sections from Pass 1 XML
    # Use regex to handle potential whitespace variations in the XML tags
    section_pattern = re.compile(
        r'<section\s+id="(\d+)">(.*?)</section>',
        re.DOTALL
    )

    def extract_tag(content: str, tag: str) -> str:
        """Extract text content of an XML tag, stripped."""
        m = re.search(rf'<{tag}>(.*?)</{tag}>', content, re.DOTALL)
        return m.group(1).strip() if m else ""

    sections = []
    for match in section_pattern.finditer(pass1_xml):
        sec_id = match.group(1)
        content = match.group(2)

        section = {
            "id": sec_id,
            "title": extract_tag(content, "title"),
            "narrative_territory": extract_tag(content, "narrative_territory"),
            "contains_chapter_break": extract_tag(content, "contains_chapter_break").lower() == "true",
            "suggested_beat_count": extract_tag(content, "suggested_beat_count"),
            "start_marker": extract_tag(content, "start_marker"),
            "end_marker": extract_tag(content, "end_marker"),
            "script_excerpt": None   # filled below
        }
        sections.append(section)

    if not sections:
        raise ValueError(
            "No <section> blocks found in Pass 1 output.\n"
            "Check that Pass 1 produced valid XML output."
        )

    # Slice the script between markers for each section
    for i, section in enumerate(sections):
        start_pos = _find_marker_position(script_normalized, section["start_marker"])

        end_marker = section["end_marker"].strip()
        if end_marker.upper() == "END":
            end_pos = len(script_normalized)
        else:
            end_pos = _find_marker_position(script_normalized, end_marker)

        if end_pos <= start_pos:
            raise ValueError(
                f"Section {section['id']} — end_marker appears before or at start_marker.\n"
                f"  start: '{section['start_marker']}'\n"
                f"  end:   '{section['end_marker']}'\n"
                f"Reorder or re-run Pass 1."
            )

        # Extract the slice from the ORIGINAL (non-normalized) script for
        # faithful reproduction. We re-locate the start using the original text.
        # Re-find in original using the normalized positions as a guide: find
        # the raw start by searching for the start_marker in the original text.
        start_marker_raw = section["start_marker"].strip()
        raw_start = script_raw.find(start_marker_raw)
        if raw_start == -1:
            # Fallback: try with normalized whitespace matching on original
            # (handles cases where the script has extra spaces/newlines in the marker span)
            raw_start = script_normalized.find(_normalize(start_marker_raw))
            excerpt = script_normalized[start_pos:end_pos]
        else:
            if end_marker.upper() == "END":
                excerpt = script_raw[raw_start:]
            else:
                end_marker_raw = end_marker.strip()
                raw_end = script_raw.find(end_marker_raw, raw_start)
                if raw_end == -1:
                    # Fallback to normalized
                    excerpt = script_normalized[start_pos:end_pos]
                else:
                    excerpt = script_raw[raw_start:raw_end]

        section["script_excerpt"] = excerpt.strip()

    return sections


def format_sections_summary(sections: list[dict]) -> str:
    """Return a human-readable summary of sliced sections for logging."""
    lines = []
    for s in sections:
        excerpt_len = len(s.get("script_excerpt") or "")
        lines.append(
            f"  Section {s['id']}: \"{s['title']}\" "
            f"| beats: {s['suggested_beat_count']} "
            f"| excerpt: {excerpt_len} chars "
            f"| chapter_break: {s['contains_chapter_break']}"
        )
    return "\n".join(lines)
