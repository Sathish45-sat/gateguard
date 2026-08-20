import os
import re
import urllib.parse
import pandas as pd
import requests

# Dataset directories
RAW_DIR = os.path.join("data", "raw")
PROCESSED_DIR = os.path.join("data", "processed")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

CSIC_DATA_URL = "https://raw.githubusercontent.com/fivethreeo/csic_2010/master/csic_2010.csv"
SECLISTS_SQLI_URL = "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/SQLi/Generic-SQLi.txt"
SECLISTS_XSS_URL = "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/XSS/XSS-Cheat-Sheet-PortSwigger.txt"

FALLBACK_NORMAL_REQUESTS = [
    "GET /index.html HTTP/1.1",
    "GET /search?q=laptop&category=electronics HTTP/1.1",
    "POST /login username=admin&password=Password123!",
    "GET /images/logo.png HTTP/1.1",
    "POST /api/v1/user/profile name=John+Doe&email=john@example.com",
    "GET /products?page=2&sort=asc HTTP/1.1",
    "GET /about-us HTTP/1.1",
    "POST /checkout item_id=402&quantity=1&payment=card",
    "GET /blog/posts/security-best-practices HTTP/1.1",
    "POST /contact message=Hello+support+team HTTP/1.1",
    "GET /assets/style.css HTTP/1.1",
    "POST /settings theme=dark&notifications=true HTTP/1.1",
    "GET /api/status HTTP/1.1",
    "GET /download/report.pdf HTTP/1.1",
    "POST /feedback rating=5&comments=Great+service HTTP/1.1",
]

FALLBACK_MALICIOUS_PAYLOADS = [
    "' OR '1'='1",
    "admin' --",
    "1 UNION SELECT null, username, password FROM users--",
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert(1)>",
    "'; DROP TABLE users; --",
    "1' AND 1=1 UNION ALL SELECT 1,2,3,table_name FROM information_schema.tables--",
    "../../../../etc/passwd",
    "| cat /etc/passwd",
    "<svg onload=alert(document.cookie)>",
    "' OR 1=1#",
    "1' HAVING 1=1--",
    "<iframe src=\"javascript:alert('XSS')\">",
    "'; EXEC xp_cmdshell('dir');--",
    "<?php system($_GET['cmd']); ?>",
]


def fetch_remote_data():
    """Fetch CSIC 2010 and SecLists datasets from remote GitHub repos if reachable."""
    normal_samples = []
    malicious_samples = []

    print("[*] Fetching CSIC 2010 & SecLists datasets...")

    try:
        r_sqli = requests.get(SECLISTS_SQLI_URL, timeout=5)
        if r_sqli.status_code == 200:
            sqli_lines = [line.strip() for line in r_sqli.text.splitlines() if line.strip() and not line.startswith("#")]
            malicious_samples.extend(sqli_lines[:50])
    except Exception:
        pass

    try:
        r_xss = requests.get(SECLISTS_XSS_URL, timeout=5)
        if r_xss.status_code == 200:
            xss_lines = [line.strip() for line in r_xss.text.splitlines() if line.strip() and not line.startswith("#")]
            malicious_samples.extend(xss_lines[:50])
    except Exception:
        pass

    try:
        r_csic = requests.get(CSIC_DATA_URL, timeout=5)
        if r_csic.status_code == 200:
            lines = r_csic.text.splitlines()
            for line in lines[1:200]:
                parts = line.split(",")
                if len(parts) >= 2:
                    req, label = parts[0], parts[-1].strip()
                    if label == "1" or "anomalous" in label.lower():
                        malicious_samples.append(req)
                    else:
                        normal_samples.append(req)
    except Exception:
        pass

    if len(normal_samples) < 10:
        normal_samples.extend(FALLBACK_NORMAL_REQUESTS)
    if len(malicious_samples) < 10:
        malicious_samples.extend(FALLBACK_MALICIOUS_PAYLOADS)

    normal_samples = list(set(normal_samples))
    malicious_samples = list(set(malicious_samples))

    return normal_samples, malicious_samples


def obfuscate_url_encode_full(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def obfuscate_url_encode_partial(s: str) -> str:
    char_map = {
        "'": "%27", '"': "%22", "<": "%3C", ">": "%3E",
        ";": "%3B", "=": "%3D", " ": "%20", "(": "%28", ")": "%29",
    }
    return "".join(char_map.get(c, c) for c in s)


def obfuscate_case_mixing(s: str) -> str:
    res = []
    for i, c in enumerate(s):
        if c.isalpha():
            res.append(c.upper() if i % 2 == 0 else c.lower())
        else:
            res.append(c)
    return "".join(res)


def obfuscate_inline_sql_comment(s: str) -> str:
    commented = s.replace(" ", "/**/")
    keywords = ["UNION", "SELECT", "WHERE", "AND", "OR", "FROM", "DROP", "INSERT", "SCRIPT", "ALERT"]
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        replacement = kw[: len(kw) // 2] + "/**/" + kw[len(kw) // 2 :]
        commented = pattern.sub(replacement, commented)
    return commented


def obfuscate_double_encoding(s: str) -> str:
    return urllib.parse.quote(urllib.parse.quote(s, safe=""), safe="")


def generate_obfuscated_variants(payload: str):
    variants = [
        (obfuscate_url_encode_full(payload), "url_encode_full"),
        (obfuscate_url_encode_partial(payload), "url_encode_partial"),
        (obfuscate_case_mixing(payload), "case_mixing"),
        (obfuscate_inline_sql_comment(payload), "sql_comment_injection"),
        (obfuscate_double_encoding(payload), "double_encoding"),
    ]
    unique_variants = []
    seen = {payload}
    for var, tech in variants:
        if var not in seen:
            seen.add(var)
            unique_variants.append((var, tech))

    if len(unique_variants) < 3:
        v_combo = obfuscate_case_mixing(obfuscate_url_encode_partial(payload))
        if v_combo not in seen:
            unique_variants.append((v_combo, "case_mix_plus_partial_url"))

    return unique_variants


def main():
    print("=== GateGuard Data Collection & Obfuscation Pipeline ===")

    normal_samples, malicious_samples = fetch_remote_data()

    print(f"[*] Raw normal samples: {len(normal_samples)}")
    print(f"[*] Raw malicious samples: {len(malicious_samples)}")

    # Assign base_sample_ids to malicious samples
    raw_records = []
    for idx, s in enumerate(normal_samples, 1):
        raw_records.append({
            "request_string": s,
            "label": 0,
            "technique": "raw",
            "base_sample_id": f"ben_raw_{idx:04d}"
        })

    mal_id_map = {}
    for idx, s in enumerate(malicious_samples, 1):
        base_id = f"mal_{idx:04d}"
        mal_id_map[s] = base_id
        raw_records.append({
            "request_string": s,
            "label": 1,
            "technique": "raw",
            "base_sample_id": base_id
        })

    df_raw = pd.DataFrame(raw_records)
    raw_csv_path = os.path.join(RAW_DIR, "malicious_raw.csv")
    df_raw.to_csv(raw_csv_path, index=False)
    print(f"[+] Saved raw dataset to {raw_csv_path} ({len(df_raw)} rows)")

    # Build processed dataset with shared base_sample_id for all obfuscated variants
    processed_records = list(raw_records)

    total_variants_count = 0
    for s in malicious_samples:
        base_id = mal_id_map[s]
        variants = generate_obfuscated_variants(s)
        total_variants_count += len(variants)
        for var_string, tech in variants:
            processed_records.append({
                "request_string": var_string,
                "label": 1,
                "technique": tech,
                "base_sample_id": base_id
            })

    df_processed = pd.DataFrame(processed_records)
    processed_csv_path = os.path.join(PROCESSED_DIR, "malicious_obfuscated.csv")
    df_processed.to_csv(processed_csv_path, index=False)

    print(f"[+] Generated {total_variants_count} obfuscated malicious variants.")
    print(f"[+] Saved processed dataset to {processed_csv_path} ({len(df_processed)} rows)")


if __name__ == "__main__":
    main()
