import os
import random
import pandas as pd

RAW_DIR = os.path.join("data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

FIRST_NAMES = [
    "John", "Sarah", "Liam", "Emma", "Noah", "Olivia", "Patrick", "Sean",
    "Maureen", "Michael", "Sophia", "James", "Isabella", "William", "Mia",
    "Benjamin", "Charlotte", "Lucas", "Amelia", "Arthur", "Connor",
    "Sathish", "Naveen", "Elena", "Marcus", "Chloe", "David", "Grace", "Daniel"
]

LAST_NAMES = [
    "Smith", "O'Connor", "D'Angelo", "O'Brien", "O'Neill", "L'Estrade",
    "N'Golo", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
]

SEARCH_QUERIES = [
    "laptop stand", "men's leather jacket", "women's running shoes",
    "baker's dozen recipes", "O'Reilly Python programming", "wireless earbuds",
    "mechanical keyboard RGB", "4k monitor 27 inch", "chef's knife set",
    "winter coat for kids", "smart watch fitness tracker", "coffee maker espresso",
    "gaming mouse high DPI", "noise cancelling headphones", "ergonomic chair",
    "docker & kubernetes guide", "python data science handbook", "usb-c hub multi-port",
    "travel backpack waterproof", "electric toothbrush rechargeable", "stainless steel water bottle",
    "bluetooth speaker portable", "standing desk converter", "webcam 1080p stream",
    "ring light for video call", "macbook pro case 14 inch", "desk pad leather", "monitor light bar"
]

CATEGORIES = [
    "electronics", "apparel", "books", "home-kitchen", "sports", "computers",
    "gaming", "office-supplies", "beauty", "automotive", "garden", "health"
]

DOMAINS = ["example.com", "mail.com", "testorg.net", "company.io", "workplace.org"]

PASSWORDS = [
    "Pass123!", "Welcome#2026", "P@ssw0rd_99", "Secure!Pass88",
    "MyDogName$2024", "Summer#Vibes!", "Coffee@Morning1", "Coding#Is#Fun",
    "GateGuard_Secure!9", "Alpha_Beta_123!", "StarWars#2025", "Keyboard!Cat9"
]

COMMENTS = [
    "Great service, really enjoyed the quick delivery!",
    "Product quality is top notch. Highly recommend!",
    "Customer support helped me with O'Connor's account issue promptly.",
    "Fast shipping and nice packaging.",
    "Very satisfied with my purchase. Will buy again!",
    "It works as expected, no complaints.",
    "The user interface is slick and easy to use.",
    "Awesome experience overall!"
]

# Legitimate benign requests that contain security keyword overlaps
KEYWORD_BENIGN_REQUESTS = [
    "GET /search?q=select+your+size&category=apparel HTTP/1.1",
    "GET /search?q=drop+shadow+effect+css&category=books HTTP/1.1",
    "POST /feedback message=Need+script+for+my+presentation HTTP/1.1",
    "POST /api/v1/user/address action=insert+new+address HTTP/1.1",
    "POST /api/v1/user/address action=delete+my+old+address HTTP/1.1",
    "POST /api/v1/user/profile action=update+my+profile HTTP/1.1",
    "GET /faq?q=where+is+my+order HTTP/1.1",
    "GET /search?q=union+of+workers+newsletter HTTP/1.1",
    "GET /search?q=cute+cat+video+compilation HTTP/1.1",
    "GET /settings?view=system+settings+for+display HTTP/1.1",
    "GET /download/exec_summary.pdf HTTP/1.1",
    "GET /search?q=alert+system+for+smart+home HTTP/1.1",
    "GET /search?q=onerror+event+handler+tutorial HTTP/1.1",
    "GET /search?q=iframe+responsive+embed+code HTTP/1.1",
    "POST /feedback comment=Please+eval+my+support+ticket HTTP/1.1",
    "GET /search?q=javascript+for+beginners+book HTTP/1.1",
    "POST /search query=powershell+scripting+guide HTTP/1.1",
    "GET /search?q=base64+encoding+explained HTTP/1.1"
]


def generate_login_request() -> str:
    first = random.choice(FIRST_NAMES).lower()
    last = random.choice(LAST_NAMES).lower().replace("'", "")
    user = f"{first}.{last}{random.randint(1, 99)}"
    pwd = random.choice(PASSWORDS)
    return f"POST /login username={user}&password={pwd}"


def generate_search_request() -> str:
    query = random.choice(SEARCH_QUERIES)
    cat = random.choice(CATEGORIES)
    page = random.randint(1, 10)
    sort = random.choice(["asc", "desc", "relevance", "price_low", "price_high"])
    return f"GET /search?q={query}&category={cat}&page={page}&sort={sort} HTTP/1.1"


def generate_profile_update_request() -> str:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    full_name = f"{first}+{last}"
    email = f"{first.lower()}.{last.lower().replace("'", "")}@{random.choice(DOMAINS)}"
    phone = f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    return f"POST /api/v1/user/profile name={full_name}&email={email}&phone={phone} HTTP/1.1"


def generate_feedback_request() -> str:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first}+{last}"
    rating = random.randint(3, 5)
    comment = random.choice(COMMENTS).replace(" ", "+")
    return f"POST /feedback name={name}&rating={rating}&comments={comment} HTTP/1.1"


def generate_static_request() -> str:
    endpoints = [
        "/index.html", "/about-us", "/contact", "/terms-of-service",
        "/privacy-policy", "/assets/css/main.css", "/assets/js/app.js",
        "/images/banner.png", "/favicon.ico", "/api/v1/health",
        "/blog/posts/security-best-practices", "/faq"
    ]
    ep = random.choice(endpoints)
    return f"GET {ep} HTTP/1.1"


def generate_benign_dataset(num_samples: int = 400):
    records = []
    generators = [
        (generate_login_request, 0.25),
        (generate_search_request, 0.30),
        (generate_profile_update_request, 0.20),
        (generate_feedback_request, 0.15),
        (generate_static_request, 0.10)
    ]

    sample_counter = 1
    for _ in range(num_samples):
        r = random.random()
        cumulative = 0.0
        selected_gen = generators[0][0]
        for gen_fn, weight in generators:
            cumulative += weight
            if r <= cumulative:
                selected_gen = gen_fn
                break

        req_str = selected_gen()
        records.append({
            "request_string": req_str,
            "label": 0,
            "technique": "raw",
            "base_sample_id": f"ben_{sample_counter:04d}"
        })
        sample_counter += 1

    # Add the explicit keyword-overlap benign samples
    for kw_req in KEYWORD_BENIGN_REQUESTS:
        records.append({
            "request_string": kw_req,
            "label": 0,
            "technique": "raw_keyword_overlap",
            "base_sample_id": f"ben_{sample_counter:04d}"
        })
        sample_counter += 1

    df = pd.DataFrame(records)
    df = df.drop_duplicates(subset=["request_string"]).reset_index(drop=True)

    out_path = os.path.join(RAW_DIR, "benign_raw.csv")
    df.to_csv(out_path, index=False)
    print(f"[+] Generated {len(df)} unique synthetic benign samples (including {len(KEYWORD_BENIGN_REQUESTS)} keyword-overlap samples).")
    print(f"[+] Saved dataset to {out_path}")
    return df


if __name__ == "__main__":
    generate_benign_dataset(num_samples=400)
