import html
import re

_LINE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bERROR\b"), "log-error"),
    (re.compile(r"\bWARN(?:ING)?\b"), "log-warn"),
    (re.compile(r"\bCaused by\b", re.IGNORECASE), "log-caused-by"),
    (re.compile(r"\bException\b"), "log-exception"),
]


def highlight_log(text: str) -> str:
    lines = text.splitlines() or [""]
    rendered = []
    for line in lines:
        escaped = html.escape(line)
        css_class = _classify(line)
        if css_class:
            rendered.append(f'<span class="{css_class}">{escaped}</span>')
        else:
            rendered.append(escaped)
    return "\n".join(rendered)


def _classify(line: str) -> str | None:
    for pattern, css_class in _LINE_RULES:
        if pattern.search(line):
            return css_class
    return None
