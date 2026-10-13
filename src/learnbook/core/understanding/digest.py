"""Deterministic extractive digest for long books."""

import math
import re
from collections import Counter
from dataclasses import dataclass

from learnbook.core.ingestion.models import DocumentSection

_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)")
_HEADING = re.compile(r"^(?:chapter\s+\d+[:.\- ]*)?(.{2,100})$", re.I)
_CUES = (
    "in summary",
    "the key",
    "important",
    "framework",
    "principle",
    "rule",
    "step",
    "method",
    "model",
    "because",
    "therefore",
    "for example",
    "remember",
    "never",
    "always",
)
_WORDS = re.compile(r"[a-z0-9']+")


@dataclass(frozen=True)
class DigestResult:
    text: str
    structure_source: str
    sections_total: int
    sections_covered: int
    pages_covered: int


@dataclass(frozen=True)
class _Sentence:
    text: str
    page: int
    position: int
    paragraph_edge: bool
    section_edge: bool
    heading_nearby: bool
    terms: frozenset[str]


def _fallback_sections(pages: list[dict[str, object]]) -> list[DocumentSection]:
    page_numbers = [int(page["page_number"]) for page in pages]
    if not page_numbers:
        return []
    heading_pages: list[tuple[str, int]] = []
    for page in pages:
        number = int(page["page_number"])
        for line in str(page["text"]).splitlines():
            line = line.strip()
            match = _HEADING.match(line)
            if not match or len(line.split()) > 14 or len(line) > 100:
                continue
            letters = [char for char in line if char.isalpha()]
            if letters and (line.isupper() or line.istitle()):
                heading_pages.append((match.group(1)[:300], number))
                break
    if len(heading_pages) >= 2:
        sections = []
        for index, (title, start) in enumerate(heading_pages):
            end = (
                heading_pages[index + 1][1] - 1
                if index + 1 < len(heading_pages)
                else page_numbers[-1]
            )
            sections.append(
                DocumentSection(
                    title=title, start_page=start, end_page=max(start, end), level=1
                )
            )
        return sections
    return [
        DocumentSection(
            title=(
                f"Pages {page_numbers[offset]} to "
                f"{page_numbers[min(offset + 9, len(page_numbers) - 1)]}"
            ),
            start_page=page_numbers[offset],
            end_page=page_numbers[min(offset + 9, len(page_numbers) - 1)],
            level=1,
        )
        for offset in range(0, len(page_numbers), 10)
    ]


def _sentences_for_section(
    section: DocumentSection,
    page_text: dict[int, str],
    heading_pages: set[int],
) -> list[_Sentence]:
    found: list[_Sentence] = []
    paragraphs: list[tuple[int, str]] = []
    for page_number in range(section.start_page, section.end_page + 1):
        text = page_text.get(page_number, "")
        paragraphs.extend(
            (page_number, part.strip())
            for part in re.split(r"\n\s*\n", text)
            if part.strip()
        )
    position = 0
    for paragraph_index, (page_number, paragraph) in enumerate(paragraphs):
        matches = [
            m.group().strip()
            for m in _SENTENCE.finditer(paragraph)
            if m.group().strip()
        ]
        for sentence_index, sentence in enumerate(matches):
            terms = frozenset(_WORDS.findall(sentence.casefold()))
            if len(terms) < 2:
                position += 1
                continue
            found.append(
                _Sentence(
                    text=sentence,
                    page=page_number,
                    position=position,
                    paragraph_edge=sentence_index in (0, len(matches) - 1),
                    section_edge=paragraph_index in (0, len(paragraphs) - 1),
                    heading_nearby=any(
                        abs(page_number - page) <= 1 for page in heading_pages
                    ),
                    terms=terms,
                )
            )
            position += 1
    return found


def build_digest(
    pages: list[dict[str, object]],
    *,
    sections: list[DocumentSection] | None = None,
    structure_source: str | None = None,
    ratio: float = 0.15,
    minimum_section_chars: int = 240,
    maximum_section_chars: int = 3200,
) -> DigestResult:
    """Select salient sentences while retaining every section's source markers."""
    if (
        not 0 < ratio <= 1
        or minimum_section_chars < 1
        or maximum_section_chars < minimum_section_chars
    ):
        raise ValueError("Digest size configuration is invalid.")
    if not pages:
        return DigestResult("", structure_source or "fallback", 0, 0, 0)
    page_text = {int(page["page_number"]): str(page["text"]) for page in pages}
    if not sections:
        sections = _fallback_sections(pages)
        source = (
            "headings"
            if sections and not sections[0].title.casefold().startswith("pages ")
            else "windows"
        )
    else:
        source = structure_source or "outline"
    cleaned_sections = [
        section
        for section in sections
        if section.start_page <= section.end_page
        and any(section.start_page <= page <= section.end_page for page in page_text)
    ]
    if not cleaned_sections:
        cleaned_sections = _fallback_sections(pages)
        source = "fallback"

    all_sentences: list[_Sentence] = []
    section_sentences: list[list[_Sentence]] = []
    heading_pages = {section.start_page for section in cleaned_sections}
    for section in cleaned_sections:
        sentences = _sentences_for_section(section, page_text, heading_pages)
        section_sentences.append(sentences)
        all_sentences.extend(sentences)
    document_frequency: Counter[str] = Counter()
    for sentence in all_sentences:
        document_frequency.update(sentence.terms)
    total_sentences = max(1, len(all_sentences))
    scored: dict[int, float] = {}
    for sentence in all_sentences:
        tfidf = sum(
            (1 + math.log(1 + sentence.terms.__len__()))
            * math.log((total_sentences + 1) / (document_frequency[term] + 1))
            for term in sentence.terms
        ) / max(1, len(sentence.terms))
        lower = sentence.text.casefold()
        cue = sum(1 for phrase in _CUES if phrase in lower)
        scored[sentence.position] = (
            tfidf
            + (1.5 if sentence.paragraph_edge else 0)
            + (2.0 if sentence.section_edge else 0)
            + (8.0 if cue else 0)
            + (0.75 if sentence.heading_nearby else 0)
        )

    selected: list[list[_Sentence]] = []
    covered_pages: set[int] = set()
    for sentences in section_sentences:
        if not sentences:
            selected.append([])
            continue
        target = min(
            maximum_section_chars,
            max(
                minimum_section_chars, int(sum(len(s.text) for s in sentences) * ratio)
            ),
        )
        ranked = sorted(
            sentences,
            key=lambda sentence: (-scored[sentence.position], sentence.position),
        )
        chosen: set[int] = set()
        size = 0
        for sentence in ranked:
            if len(chosen) > 0 and size + len(sentence.text) > target:
                continue
            chosen.add(sentence.position)
            size += len(sentence.text)
            if size >= target:
                break
        if not chosen:
            chosen.add(ranked[0].position)
        ordered = sorted(
            (sentence for sentence in sentences if sentence.position in chosen),
            key=lambda s: s.position,
        )
        selected.append(ordered)
        covered_pages.update(sentence.page for sentence in ordered)
    output: list[str] = []
    for section, sentences in zip(cleaned_sections, selected, strict=True):
        if not sentences:
            continue
        output.append(f"## {section.title}")
        current_page = None
        for sentence in sentences:
            if sentence.page != current_page:
                output.append(f"[p.{sentence.page}]")
                current_page = sentence.page
            output.append(sentence.text)
    return DigestResult(
        text="\n".join(output),
        structure_source=source,
        sections_total=len(cleaned_sections),
        sections_covered=sum(bool(items) for items in selected),
        pages_covered=len(covered_pages),
    )
