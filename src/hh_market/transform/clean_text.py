"""HTML and whitespace normalization for vacancy descriptions."""

import re
from html import unescape

from bs4 import BeautifulSoup


def html_to_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = BeautifulSoup(value, "html.parser").get_text(" ")
    text = unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip() or None


def normalize_text(value: str | None) -> str | None:
    text = html_to_text(value)
    return text.casefold() if text else None
