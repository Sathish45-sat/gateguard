import math
import re
import urllib.parse
from collections import Counter

# Security attack keyword strings & regex patterns
SECURITY_KEYWORDS = [
    "select", "union", "drop", "insert", "update", "delete", "exec", "execute",
    "script", "alert", "onerror", "onload", "eval", "javascript", "iframe",
    "1=1", "--", "information_schema", "xp_cmdshell",
    "etc/passwd", "cat ", "system(", "base64", "cmd.exe", "powershell"
]

# Regex patterns for flexible matching (e.g. OR '1'='1' with or without spaces/comments)
REGEX_SECURITY_PATTERNS = [
    r"or\s*['\"]?1['\"]?\s*=\s*['\"]?1",  # OR 1=1, OR '1'='1', OR'1'='1'
    r"and\s*['\"]?1['\"]?\s*=\s*['\"]?1", # AND 1=1, AND '1'='1'
]


def calculate_entropy(s: str) -> float:
    """Calculate character-level Shannon entropy of string."""
    if not s:
        return 0.0
    length = len(s)
    counts = Counter(s)
    entropy = -sum((count / length) * math.log2(count / length) for count in counts.values())
    return round(entropy, 4)


def calculate_keyword_count(s: str) -> int:
    """
    Count occurrence of SQL/XSS/command injection keywords.
    Strips inline comments (like /**/) and URL-decodes the string first.
    """
    if not s:
        return 0

    # 1. URL-decode the string (try decoding up to twice for double-encoding)
    decoded = urllib.parse.unquote(urllib.parse.unquote(s))

    # 2. Strip inline comments like /*...*/ or /**/
    cleaned = re.sub(r"/\*.*?\*/", "", decoded, flags=re.DOTALL)
    cleaned_lower = cleaned.lower()

    total_count = 0

    # Match literal keywords
    for kw in SECURITY_KEYWORDS:
        total_count += cleaned_lower.count(kw.lower())

    # Match regex patterns
    for pat in REGEX_SECURITY_PATTERNS:
        matches = re.findall(pat, cleaned_lower)
        total_count += len(matches)

    return total_count


def calculate_special_char_ratio(s: str) -> float:
    """Calculate ratio of non-alphanumeric, non-space characters relative to length."""
    if not s:
        return 0.0
    special_count = sum(1 for c in s if not c.isalnum() and not c.isspace())
    return round(special_count / len(s), 4)


def extract_features(request_string: str) -> dict:
    """
    Extract feature vector for GateGuard request scoring contract:
    {
        'entropy': float,
        'length': int,
        'keyword_count': int,
        'special_char_ratio': float
    }
    """
    req_str = str(request_string) if request_string is not None else ""
    return {
        "entropy": calculate_entropy(req_str),
        "length": len(req_str),
        "keyword_count": calculate_keyword_count(req_str),
        "special_char_ratio": calculate_special_char_ratio(req_str),
    }
