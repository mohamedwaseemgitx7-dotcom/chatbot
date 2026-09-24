"""
Request text validation.
"""
import re

# Control characters except tab (\x09) and newline (\x0a), which farmers use in multi-line questions.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def sanitize_input_text(text: str) -> str:
    """Removes control characters and surrounding whitespace; keeps line breaks."""
    return _CONTROL.sub("", text).strip()
