from __future__ import annotations

import bleach
import html
import markdown as md
import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
    "div",
    "p",
    "pre",
    "code",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "blockquote",
    "span",
    "img",
    "figure",
    "figcaption",
}

_ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "rel"],
    "div": ["class"],
    "code": ["class"],
    "span": ["class"],
    "img": ["src", "alt", "title", "width", "height", "loading", "class"],
    "th": ["colspan", "rowspan", "align"],
    "td": ["colspan", "rowspan", "align"],
}

_ALLOWED_PROTOCOLS = set(bleach.sanitizer.ALLOWED_PROTOCOLS) | {"mailto"}


_INLINE_HEADING_RE = re.compile(r"(?<!\n)[ \t]+(#{1,6}\s)")
_INLINE_FENCE_RE = re.compile(r"(?<!\n)```")
_INLINE_FENCE_WITH_CODE_RE = re.compile(r"^```([a-zA-Z0-9_+-]+)?[ \t]+(.+)$")
_DIV_OPEN_RE = re.compile(r"<div(?![^>]*\bmarkdown=)([^>]*)>", flags=re.IGNORECASE)
_CODE_LINE_RE = re.compile(
    r"^\s*(?:"
    r"print\(|"
    r"for\s+\w+|while\s+|if\s+|elif\s+|else:|"
    r"def\s+\w+|class\s+\w+|return\b|"
    r"import\b|from\b|"
    r"[A-Za-z_][A-Za-z0-9_]*\s*=|"
    r"console\.log\(|let\s+|const\s+|var\s+"
    r")"
)


def _auto_fence_code_blocks(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    in_fence = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue

        if not in_fence and _CODE_LINE_RE.match(line):
            block: list[str] = []
            while i < len(lines):
                current = lines[i]
                current_stripped = current.strip()

                if current_stripped.startswith("```"):
                    break

                if current_stripped == "":
                    # Keep empty lines inside block only if another code line follows.
                    if i + 1 < len(lines) and _CODE_LINE_RE.match(lines[i + 1]):
                        block.append(current)
                        i += 1
                        continue
                    break

                if _CODE_LINE_RE.match(current):
                    block.append(current)
                    i += 1
                    continue
                break

            if block:
                out.append("```python")
                out.extend(block)
                out.append("```")
            continue

        out.append(line)
        i += 1

    return "\n".join(out)


def _normalize_inline_fence_lines(text: str) -> str:
    normalized: list[str] = []
    for raw_line in text.split("\n"):
        m = _INLINE_FENCE_WITH_CODE_RE.match(raw_line.strip())
        if not m:
            normalized.append(raw_line)
            continue

        lang = m.group(1) or ""
        code = m.group(2)
        fence_header = f"```{lang}".rstrip()
        normalized.extend([fence_header, code])

    return "\n".join(normalized)


def _normalize_markdown_input(value: str) -> str:
    # Decode copied HTML entities like &quot; and handle double-escaped text.
    text = value
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded

    # Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")
    # Normalize typographic quotes from messengers/docs to plain quotes.
    text = text.translate(
        str.maketrans(
            {
                "«": '"',
                "»": '"',
                "“": '"',
                "”": '"',
                "„": '"',
                "‟": '"',
                "‘": "'",
                "’": "'",
                "‚": "'",
                "‛": "'",
            }
        )
    )

    # If headings/fences were pasted inline in one paragraph, force line breaks.
    text = _INLINE_HEADING_RE.sub(r"\n\n\1", text)
    text = _INLINE_FENCE_RE.sub("\n```", text)
    text = _normalize_inline_fence_lines(text)
    # Enable markdown parsing inside user HTML blocks (cards/grids from Tailwind).
    text = _DIV_OPEN_RE.sub(r'<div\1 markdown="1">', text)
    text = _auto_fence_code_blocks(text)

    return text


@register.filter(name="render_markdown")
def render_markdown(value: str) -> str:
    if not value:
        return ""

    prepared = _normalize_markdown_input(str(value))

    html = md.markdown(
        prepared,
        extensions=[
            "extra",
            "sane_lists",
            "fenced_code",
            "tables",
            "nl2br",
            "md_in_html",
        ],
    )
    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    return mark_safe(cleaned)
