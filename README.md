# GateGuard ML Pipeline

GateGuard is a request-scoring security tool designed to analyze web incoming requests and detect malicious patterns using machine learning models.

---

## Project Structure

```text
gateguard/
├── data/
│   ├── raw/          # Raw datasets
│   └── processed/    # Preprocessed and engineered datasets
├── models/           # Trained model artifacts and ONNX exports
├── notebooks/        # Exploratory data analysis notebooks
├── src/              # Source scripts for data parsing, training & inference
├── main.py           # FastAPI service endpoint
├── requirements.txt  # Project dependencies
└── README.md         # Project documentation & contract specification
```

---

## Data Contracts

### 1. Feature Vector Contract

The feature vector represents the numerical extraction of security-relevant attributes from an incoming request payload or string.

| Field | Type | Description |
| :--- | :--- | :--- |
| `entropy` | `float` | Shannon entropy of the request payload or target string. Higher entropy often correlates with encoded/encrypted malicious payloads or obfuscated commands. |
| `length` | `int` | Character/byte length of the request payload or target string. |
| `keyword_count` | `int` | Total count of suspicious security keywords (e.g. SQL injection keywords, XSS tags, command injection signatures). |
| `special_char_ratio` | `float` | Ratio of non-alphanumeric special characters (`%`, `'`, `"`, `;`, `<`, `>`, `$`, etc.) relative to the total length. |

#### JSON Schema Example:
```json
{
  "entropy": 4.52,
  "length": 128,
  "keyword_count": 3,
  "special_char_ratio": 0.1875
}
```

---

### 2. Scoring Contract

The scoring interface defines the request/response exchange between the GateGuard Proxy filter and the ML Scoring Engine.

- **Request**: The proxy extracts features from incoming HTTP requests and sends the feature vector payload to the scoring endpoint.
- **Response**: The ML service evaluates the feature vector and returns a risk score evaluation.

#### Response Format:
```json
{
  "risk_score": 85.5
}
```

- **`risk_score`** (`float`, range `0` to `100`):
  - **`0 - 30`**: Low Risk (Allowed / Clean traffic)
  - **`31 - 70`**: Medium Risk (Flagged for heightened inspection / logging)
  - **`71 - 100`**: High Risk (Blocked / Quarantined)

---

## Getting Started

### Installation

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

### Running the Demo Service

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
