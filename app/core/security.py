"""
Security utilities.

Yeh module security-related helpers rakhta hai:
    - PDF magic bytes check
    - Filename sanitization (path traversal prevent)
    - Prompt injection detection
    - Simple in-memory rate limiter
"""

import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# ================================================================
# PDF magic bytes
# ================================================================

# PDF files start with "%PDF-" (5 bytes)
PDF_MAGIC = b"%PDF-"

# Aur bhi common signatures (defense in depth)
FORBIDDEN_SIGNATURES = [
    b"PK\x03\x04",        # ZIP / DOCX / XLSX
    b"\x89PNG",           # PNG
    b"\xff\xd8\xff",      # JPEG
    b"GIF87a", b"GIF89a", # GIF
    b"\x7fELF",           # ELF (Linux executable)
    b"MZ",                # Windows executable
    b"<?php",             # PHP
    b"<script",           # HTML/JS
]


def is_valid_pdf_file(file_path: Path) -> Tuple[bool, str]:
    """
    Check karo ke file asal me PDF hai (bytes se, extension se nahi).

    Returns:
        (is_valid, error_message)
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(512)
    except Exception as e:
        return False, f"File read error: {e}"

    if not header:
        return False, "File khaali hai."

    # PDF magic bytes check
    if not header.startswith(PDF_MAGIC):
        # Detect what it actually is (helpful error message)
        for sig in FORBIDDEN_SIGNATURES:
            if header.startswith(sig):
                kind = {
                    b"PK\x03\x04": "ZIP/DOCX",
                    b"\x89PNG": "PNG image",
                    b"\xff\xd8\xff": "JPEG image",
                    b"GIF87a": "GIF image",
                    b"GIF89a": "GIF image",
                    b"\x7fELF": "Linux executable",
                    b"MZ": "Windows executable",
                    b"<?php": "PHP script",
                    b"<script": "HTML/JS",
                }.get(sig, "unknown")
                return False, f"Yeh asal me PDF nahi — detect: {kind}"

        return False, "Yeh PDF file nahi (magic bytes match nahi)."

    return True, ""


# ================================================================
# Filename sanitization
# ================================================================

# Allow: letters, digits, spaces, dash, underscore, dot
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._\- ]+")

# Windows reserved names
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5",
    "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
    "LPT6", "LPT7", "LPT8", "LPT9",
}

MAX_FILENAME_LENGTH = 200


def sanitize_filename(filename: str) -> str:
    """
    Filename ko safe banao (path traversal, reserved names hatao).

    Example:
        "../../etc/passwd.pdf"  →  "etc_passwd.pdf"
        "CON.pdf"               →  "file_CON.pdf"
        "hello*world.pdf"       →  "hello_world.pdf"
    """
    if not filename:
        return "upload.pdf"

    # Sirf basename lo
    name = Path(filename).name

    # Path separators hatao
    name = name.replace("/", "_").replace("\\", "_")

    # Unsafe characters hatao
    name = SAFE_FILENAME_RE.sub("_", name)

    # Multiple underscores/spaces collapse
    name = re.sub(r"_+", "_", name)
    name = re.sub(r" +", " ", name)

    # Leading/trailing dots, spaces, underscores hatao
    name = name.strip(". _")

    # Khaali ho gaya? Default
    if not name:
        return "upload.pdf"

    # Windows reserved name?
    stem = name.split(".")[0].upper()
    if stem in WINDOWS_RESERVED:
        name = f"file_{name}"

    # Length limit
    if len(name) > MAX_FILENAME_LENGTH:
        # Extension preserve karo
        p = Path(name)
        stem = p.stem[: MAX_FILENAME_LENGTH - len(p.suffix) - 5]
        name = f"{stem}{p.suffix}"

    # Extension check (final)
    if not name.lower().endswith(".pdf"):
        # Extension hatao aur PDF lagao
        if "." in name:
            name = name.rsplit(".", 1)[0] + ".pdf"
        else:
            name = name + ".pdf"

    return name


# ================================================================
# Prompt injection detection
# ================================================================

# Common injection phrases jo document me ho sakti hain
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) (instructions|prompts|rules)",
    r"disregard (all )?(previous|prior|above) (instructions|prompts|rules)",
    r"forget (all )?(previous|prior|above) (instructions|prompts|rules)",
    r"you are now (a|an)?\s*\w+",
    r"new instructions?:",
    r"system:?\s*you",
    r"assistant:?\s*you",
    r"\[system\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"<\|system\|>",
    r"<\|user\|>",
    r"<\|assistant\|>",
    r"###\s*(system|instruction|prompt)",
    r"act as (a|an)?\s*\w+",
    r"pretend (to be|you are)",
    r"jailbreak",
]

INJECTION_RE = re.compile(
    "|".join(f"({p})" for p in INJECTION_PATTERNS),
    re.IGNORECASE,
)


def detect_injection(text: str) -> List[str]:
    """
    Text me prompt injection attempts dhoondho.

    Returns:
        List of matched patterns (khaali list = safe).
    """
    if not text:
        return []
    matches = []
    for m in INJECTION_RE.finditer(text):
        matches.append(m.group(0)[:80])  # truncate
    return matches


def sanitize_context_for_llm(text: str) -> str:
    """
    Context ko LLM ko bhejne se pehle sanitize karo.

    Simple approach: suspicious patterns ko neutralize karo taake LLM
    unhe instructions na samjhe.

    Note: Yeh perfect nahi hai — asli defense system prompt me hai.
    """
    if not text:
        return text

    # Common injection markers ko replace karo
    # Instruction-like tokens → harmless text
    text = re.sub(
        r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+"
        r"(instructions?|prompts?|rules?)",
        "[redacted instruction-like text]",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<\|[a-z_]+\|>", "[redacted]", text)
    text = re.sub(
        r"^(system|assistant|user)\s*:",
        "[redacted]:",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    return text


# ================================================================
# Simple in-memory rate limiter
# ================================================================

class RateLimiter:
    """
    Simple sliding-window rate limiter (per key — IP, user, etc.).

    Production me Redis ya similar use karna chahiye.
    Dev/small scale ke liye yeh theek hai.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str) -> Tuple[bool, Optional[int]]:
        """
        Check karo ke is key ki request allow karni chahiye.

        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Purane timestamps hatao
        hits = self._hits[key]
        hits[:] = [t for t in hits if t > cutoff]

        if len(hits) >= self.max_requests:
            # Limit cross — retry after
            oldest = hits[0]
            retry_after = int(oldest + self.window_seconds - now) + 1
            return False, retry_after

        hits.append(now)
        return True, None

    def reset(self, key: Optional[str] = None) -> None:
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)


# Global limiters
upload_limiter = RateLimiter(max_requests=20, window_seconds=60)   # 20 uploads/min
ask_limiter = RateLimiter(max_requests=60, window_seconds=60)      # 60 asks/min


def get_client_ip(request) -> str:
    """FastAPI Request se client IP nikalo (proxies handle karo)."""
    # X-Forwarded-For (reverse proxy ke peeche)
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real
    if request.client:
        return request.client.host
    return "unknown"