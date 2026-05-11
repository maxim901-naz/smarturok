from __future__ import annotations

import bleach
import markdown as md
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


@register.filter(name="render_markdown")
def render_markdown(value: str) -> str:
    if not value:
        return ""

    html = md.markdown(
        value,
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
