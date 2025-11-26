import re
from html import unescape

# PUBLIC_INTERFACE
def basic_text_cleanup(text: str) -> str:
    """
    Perform simple cleanup:
    - Unescape HTML entities
    - Normalize whitespace
    - Strip leading/trailing spaces
    """
    if not text:
        return ""
    t = unescape(text)
    t = re.sub(r"\r\n?", "\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()
