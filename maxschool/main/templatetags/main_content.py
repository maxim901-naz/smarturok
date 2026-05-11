from __future__ import annotations

import bleach
import html
import markdown as md
import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
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
}

_ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "a": ["href", "title", "rel"],
    "code": ["class"],
    "span": ["class"],
    "th": ["colspan", "rowspan", "align"],
    "td": ["colspan", "rowspan", "align"],
}

_ALLOWED_PROTOCOLS = set(bleach.sanitizer.ALLOWED_PROTOCOLS) | {"mailto"}


_INLINE_HEADING_RE = re.compile(r"(?<!\n)[ \t]+(#{1,6}\s)")
_INLINE_FENCE_RE = re.compile(r"(?<!\n)```")


def _normalize_markdown_input(value: str) -> str:
    # Decode copied HTML entities like &quot; and normalize line endings.
    text = html.unescape(value).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")

    # If headings/fences were pasted inline in one paragraph, force line breaks.
    text = _INLINE_HEADING_RE.sub(r"\n\n\1", text)
    text = _INLINE_FENCE_RE.sub("\n```", text)

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
        ],
    )
    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned = bleach.linkify(cleaned, skip_tags=["pre", "code"])
    return mark_safe(cleaned)
