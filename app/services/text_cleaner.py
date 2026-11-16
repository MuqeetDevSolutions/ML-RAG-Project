"""
Text cleaning service.

PDF se nikla text aksar gandha hota hai:
- Ek se zyada spaces
- Tabs aur non-breaking spaces
- 3+ consecutive newlines (paragraph gaps)
- Hyphenated word breaks ("infor-\nmation" -> "information")
- Control characters (invisible junk)

Yeh module us text ko RAG ke liye saaf karta hai — lekin
bilkul khatam nahi karta (paragraph structure mehfooz rehti hai).
"""

import re


# Ek se zyada spaces/tabs -> single space
_MULTI_SPACE = re.compile(r"[ \t]+")

# 3 ya us se zyada newlines -> 2 newlines (paragraph break)
_MULTI_NEWLINE = re.compile(r"\n{3,}")

# Line break ke sath hyphen: "infor-\nmation" -> "information"
# Note: keval lowercase letters ke darmiyan hyphen+newline ko join karte hain,
# warna "COVID-19\nreport" jaisa case galat join ho jata.
_HYPHEN_LINEBREAK = re.compile(r"([a-zA-Z])-\n([a-z])")

# Non-printable / control characters (newline, tab ko chhod kar)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    """
    Raw extracted text ko saaf karo.

    Steps:
        1. Control characters hatao.
        2. Hyphenated line breaks join karo.
        3. Har line ke aage/peeche ke spaces trim karo.
        4. Multiple spaces -> single space.
        5. 3+ newlines -> 2 newlines (paragraph break).
        6. Aakhir me strip() karo.

    Args:
        text: Raw text.

    Returns:
        Cleaned text.
    """
    if not text:
        return ""

    # 1. Invisible control characters hatao
    text = _CONTROL_CHARS.sub("", text)

    # 2. Hyphen line break join: "infor-\nmation" -> "information"
    text = _HYPHEN_LINEBREAK.sub(r"\1\2", text)

    # 3. Har line ko trim karo (leading/trailing spaces)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 4. Multiple spaces -> single space
    text = _MULTI_SPACE.sub(" ", text)

    # 5. 3+ newlines -> 2 newlines
    text = _MULTI_NEWLINE.sub("\n\n", text)

    return text.strip()


def clean_pages(pages):
    """
    Ek list of PageText objects leta hai (pdf_reader se),
    har page ka text clean karta hai, aur wahi list wapas deta hai
    (char_count update ke sath).

    Args:
        pages: List[PageText]

    Returns:
        List[PageText] (in-place updates ke sath)
    """
    for page in pages:
        page.text = clean_text(page.text)
        page.char_count = len(page.text)
    return pages