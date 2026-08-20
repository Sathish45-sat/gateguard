# GateGuard Model Integration Handoff & Technical Specification

This document details everything required to integrate the trained GateGuard ML request-scoring model into the Go proxy service.

---

## 1. Feature Extraction Specification

The Go proxy must extract a **4-dimensional feature vector** (`[entropy, length, keyword_count, special_char_ratio]`) from each incoming HTTP request string before passing it to the ONNX model.

### Feature 1: `entropy` (float32)
Character-level Shannon entropy of the raw request string.

- **Formula**:
  $$H(X) = -\sum_{c \in S} P(c) \log_2 P(c)$$
  where $P(c) = \frac{\text{count}(c)}{\text{len}(S)}$.
- **Pseudocode**:
  ```go
  func CalculateEntropy(s string) float32 {
      if len(s) == 0 {
          return 0.0
      }
      counts := make(map[rune]float64)
      for _, char := range s {
          counts[char]++
      }
      length := float64(len(s))
      var entropy float64 = 0.0
      for _, count := range counts {
          p := count / length
          entropy -= p * math.Log2(p)
      }
      return float32(entropy)
  }
  ```

---

### Feature 2: `length` (float32)
The total character length of the raw request string (`len(s)`).

---

### Feature 3: `keyword_count` (float32)
Count of SQL injection, XSS, and command injection keywords/signatures.

- **Pre-processing Steps** (CRITICAL for matching obfuscated attacks):
  1. **URL-Decode**: Perform URL decoding on the string (decode up to 2 times for double-encoding).
  2. **Strip Inline Comments**: Strip SQL inline comments matching `/\*.*?\*/` (e.g., `UN/**/ION` becomes `UNION`).
  3. **Case-Insensitive Match**: Convert to lowercase before matching.

- **Exact Keyword List**:
  - `select`, `union`, `drop`, `insert`, `update`, `delete`, `exec`, `execute`
  - `script`, `alert`, `onerror`, `onload`, `eval`, `javascript`, `iframe`
  - `1=1`, `--`, `information_schema`, `xp_cmdshell`
  - `etc/passwd`, `cat `, `system(`, `base64`, `cmd.exe`, `powershell`

- **Regex Attack Patterns**:
  - `or\s*['"]?1['"]?\s*=\s*['"]?1` (Matches `OR 1=1`, `OR '1'='1'`, `OR'1'='1`)
  - `and\s*['"]?1['"]?\s*=\s*['"]?1` (Matches `AND 1=1`, `AND '1'='1'`)

- **Pseudocode**:
  ```go
  func CalculateKeywordCount(s string) float32 {
      // 1. URL decode
      decoded, _ := url.QueryUnescape(s)
      decoded, _ = url.QueryUnescape(decoded)

      // 2. Strip inline comments /*...*/
      reComment := regexp.MustCompile(`/\*.*?\*/`)
      cleaned := reComment.ReplaceAllString(decoded, "")
      cleanedLower := strings.ToLower(cleaned)

      count := 0
      for _, kw := range keywordList {
          count += strings.Count(cleanedLower, kw)
      }

      // Regex pattern matches
      reOR := regexp.MustCompile(`(?i)or\s*['"]?1['"]?\s*=\s*['"]?1`)
      reAND := regexp.MustCompile(`(?i)and\s*['"]?1['"]?\s*=\s*['"]?1`)

      count += len(reOR.FindAllString(cleanedLower, -1))
      count += len(reAND.FindAllString(cleanedLower, -1))

      return float32(count)
  }
  ```

---

### Feature 4: `special_char_ratio` (float32)
Ratio of non-alphanumeric, non-space characters relative to total string length.

- **Definition of Special Character**: Any character where `!isAlphanumeric(c)` and `!isSpace(c)`.
- **Formula**:
  $$\text{special\_char\_ratio} = \frac{\text{count\_special\_chars}}{\text{len}(S)}$$
- **Pseudocode**:
  ```go
  func CalculateSpecialCharRatio(s string) float32 {
      if len(s) == 0 {
          return 0.0
      }
      specialCount := 0
      for _, r := range s {
          if !unicode.IsLetter(r) && !unicode.IsDigit(r) && !unicode.IsSpace(r) {
              specialCount++
          }
      }
      return float32(specialCount) / float32(len(s))
  }
  ```

---

## 2. ONNX Model Usage & Scoring Contract

### Model File & Tensor Interface
- **Model Path**: [`models/gateguard_model.onnx`](file:///c:/Users/navee/Downloads/gateguard/models/gateguard_model.onnx)
- **Input Tensor Name**: `"input"`
- **Input Tensor Shape**: `[None, 4]` (`float32`)
- **Input Feature Ordering** (MUST follow this exact index order):
  $$\text{Input Vector} = [\text{entropy}, \text{length}, \text{keyword\_count}, \text{special\_char\_ratio}]$$

### Output & Risk Score Calculation
- **Model Output**: Output probability $P(\text{malicious}) \in [0.0, 1.0]$.
- **Risk Score Mapping**: Convert model output probability to the GateGuard `0-100` risk score contract:
  $$\text{risk\_score} = P(\text{malicious}) \times 100.0$$

### Recommended Go ONNX Library
We recommend using **`github.com/yalue/onnxruntime_go`** for binding ONNX Runtime C-shared library in Go.

#### Go Integration Pseudocode:
```go
package main

import (
    ort "github.com/yalue/onnxruntime_go"
)

func ScoreRequest(reqStr string) (float32, error) {
    // 1. Extract feature vector
    entropy := CalculateEntropy(reqStr)
    length := float32(len(reqStr))
    kwCount := CalculateKeywordCount(reqStr)
    specialRatio := CalculateSpecialCharRatio(reqStr)

    // Tensor shape: [1, 4]
    inputData := []float32{entropy, length, kwCount, specialRatio}
    inputShape := ort.NewShape(1, 4)

    inputTensor, err := ort.NewTensor(inputShape, inputData)
    defer inputTensor.Destroy()

    // 2. Run ONNX Session inference
    outputTensor, err := session.Run([]ort.ArbitraryTensor{inputTensor})
    defer outputTensor.Destroy()

    // 3. Extract probability and scale to 0-100 risk_score
    probMalicious := outputTensor[1].GetData().([]float32)[1]
    riskScore := probMalicious * 100.0

    return riskScore, nil
}
```

---

## 3. Model Performance Summary

From [`models/metrics.txt`](file:///c:/Users/navee/Downloads/gateguard/models/metrics.txt):

- **Evaluation Statement**:
  > *Evaluated on N=98 test samples (16 malicious, 82 benign), synthetic + CSIC 2010 + OWASP SecLists dataset.*

- **Dataset Split**:
  - Total Samples: 491
  - Train Set: 393 rows (80.04%, 340 groups)
  - Test Set: 98 rows (19.96%, 85 groups - zero group leakage)

- **Performance Metrics**:
  - **Overall Accuracy**: `100.00%` (`1.0000`)
  - **Benign Class**: Precision: `1.00` | Recall: `1.00` | F1: `1.00`
  - **Malicious Class**: Precision: `1.00` | Recall: `1.00` | F1: `1.00`

- **Confusion Matrix**:
  ```text
  [[75,  0]   (True Benign: 75, False Positives: 0)
   [ 0, 11]]  (False Negatives: 0, True Malicious: 11)
  ```

---

## 4. Known Limitations

1. **Small Test Set Size**:
   - The test set consists of $N=98$ samples ($16$ malicious, $82$ benign). Results are directional and serve as a baseline proof-of-concept rather than production-grade assurance.
2. **Synthetic / Seed Data Composition**:
   - Trained on synthetic requests + CSIC 2010 HTTP dataset + OWASP SecLists payload seeds. It has not yet been fine-tuned on live production traffic distributions.
3. **Keyword List Dependency**:
   - `keyword_count` relies on a fixed signature/keyword vocabulary. Zero-day attacks or novel attack payloads utilizing entirely unknown keywords will rely more heavily on `entropy` and `special_char_ratio` signals for detection.
