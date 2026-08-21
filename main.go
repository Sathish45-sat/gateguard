package main

import (
	"bytes"
	"context"
	"crypto/md5"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/alicebob/miniredis/v2"
	lru "github.com/hashicorp/golang-lru/v2"
	"github.com/redis/go-redis/v9"
	ort "github.com/yalue/onnxruntime_go"
)

const (
	RISK_THRESHOLD_LOW  = 65
	RISK_THRESHOLD_HIGH = 85
)

// Security keywords and regex patterns as defined in HANDOFF.md
var securityKeywords = []string{
	"select", "union", "drop", "insert", "update", "delete", "exec", "execute",
	"script", "alert", "onerror", "onload", "eval", "javascript", "iframe",
	"1=1", "--", "information_schema", "xp_cmdshell",
	"etc/passwd", "cat ", "system(", "base64", "cmd.exe", "powershell",
}

var reOR = regexp.MustCompile(`(?i)or\s*['"]?1['"]?\s*=\s*['"]?1`)
var reAND = regexp.MustCompile(`(?i)and\s*['"]?1['"]?\s*=\s*['"]?1`)
var reSQLComment = regexp.MustCompile(`/\*.*?\*/`)

// LogEntry represents a single request log for the dashboard API.
type LogEntry struct {
	Timestamp        string `json:"timestamp"`
	Path             string `json:"path"`
	SessionTokenHash string `json:"session_token_hash"`
	RiskScore        *int   `json:"risk_score"` // Pointer to int: null when not scored (e.g. pre-check blocklisted)
	Tier             string `json:"tier"`       // "clean", "challenged", "suspicious", "killed", "blocklisted"
	Action           string `json:"action"`     // "forwarded", "rejected_403", "rejected_401"
}

func intPtr(v int) *int {
	return &v
}

// LogBuffer stores an in-memory ring buffer of up to capacity log entries.
type LogBuffer struct {
	mu       sync.RWMutex
	logs     []LogEntry
	capacity int
}

func NewLogBuffer(capacity int) *LogBuffer {
	return &LogBuffer{
		logs:     make([]LogEntry, 0, capacity),
		capacity: capacity,
	}
}

func (b *LogBuffer) Add(entry LogEntry) {
	b.mu.Lock()
	defer b.mu.Unlock()

	if len(b.logs) >= b.capacity {
		b.logs = b.logs[1:]
	}
	b.logs = append(b.logs, entry)
}

func (b *LogBuffer) GetLogs() []LogEntry {
	b.mu.RLock()
	defer b.mu.RUnlock()

	result := make([]LogEntry, len(b.logs))
	copy(result, b.logs)
	return result
}

var globalLogBuffer = NewLogBuffer(100)

// ONNX Evaluator
type ONNXEvaluator struct {
	modelPath   string
	inputName   string
	outputNames []string
}

var globalEvaluator *ONNXEvaluator

func initONNXModel(modelPath string) (*ONNXEvaluator, error) {
	dllPath := "onnxruntime.dll"
	if _, err := os.Stat(dllPath); err != nil {
		dllPath = "d:\\Downloads\\Hackathon\\Hack_INNOV\\gateguard\\onnxruntime.dll"
	}

	ort.SetSharedLibraryPath(dllPath)
	err := ort.InitializeEnvironment()
	if err != nil {
		return nil, fmt.Errorf("ONNX InitializeEnvironment failed: %w", err)
	}

	inputs, outputs, err := ort.GetInputOutputInfo(modelPath)
	if err != nil {
		return nil, fmt.Errorf("ONNX GetInputOutputInfo failed: %w", err)
	}

	inputName := inputs[0].Name
	outputNames := []string{outputs[0].Name, outputs[1].Name}

	evaluator := &ONNXEvaluator{
		modelPath:   modelPath,
		inputName:   inputName,
		outputNames: outputNames,
	}

	log.Printf("[ONNX INIT] Successfully loaded model from %s (Input: %s, Outputs: %v)", modelPath, inputName, outputNames)
	return evaluator, nil
}

// Feature Extraction Functions
func calculateEntropy(s string) float32 {
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

func calculateKeywordCount(s string) float32 {
	if len(s) == 0 {
		return 0.0
	}

	decoded, err := url.QueryUnescape(s)
	if err != nil {
		decoded = s
	}
	decoded2, err := url.QueryUnescape(decoded)
	if err == nil {
		decoded = decoded2
	}

	cleaned := reSQLComment.ReplaceAllString(decoded, "")
	cleanedLower := strings.ToLower(cleaned)

	count := 0
	for _, kw := range securityKeywords {
		count += strings.Count(cleanedLower, kw)
	}

	count += len(reOR.FindAllString(cleanedLower, -1))
	count += len(reAND.FindAllString(cleanedLower, -1))

	return float32(count)
}

func calculateSpecialCharRatio(s string) float32 {
	if len(s) == 0 {
		return 0.0
	}
	specialCount := 0
	for _, r := range s {
		if !strings.ContainsRune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \t\n\r", r) {
			specialCount++
		}
	}
	return float32(specialCount) / float32(len(s))
}

func extractFeatures(s string) []float32 {
	entropy := calculateEntropy(s)
	length := float32(len(s))
	kwCount := calculateKeywordCount(s)
	specialRatio := calculateSpecialCharRatio(s)

	return []float32{entropy, length, kwCount, specialRatio}
}

func (e *ONNXEvaluator) Score(reqStr string) (float32, []float32, error) {
	feats := extractFeatures(reqStr)

	inputShape := ort.NewShape(1, 4)
	inputTensor, err := ort.NewTensor(inputShape, feats)
	if err != nil {
		return 0, feats, err
	}
	defer inputTensor.Destroy()

	outputLabelShape := ort.NewShape(1)
	outputLabelTensor, err := ort.NewEmptyTensor[int64](outputLabelShape)
	if err != nil {
		return 0, feats, err
	}
	defer outputLabelTensor.Destroy()

	outputProbShape := ort.NewShape(1, 2)
	outputProbTensor, err := ort.NewEmptyTensor[float32](outputProbShape)
	if err != nil {
		return 0, feats, err
	}
	defer outputProbTensor.Destroy()

	session, err := ort.NewAdvancedSession(
		e.modelPath,
		[]string{e.inputName},
		e.outputNames,
		[]ort.ArbitraryTensor{inputTensor},
		[]ort.ArbitraryTensor{outputLabelTensor, outputProbTensor},
		nil,
	)
	if err != nil {
		return 0, feats, err
	}
	defer session.Destroy()

	err = session.Run()
	if err != nil {
		return 0, feats, err
	}

	probs := outputProbTensor.GetData()
	pMalicious := float32(0.0)
	if len(probs) >= 2 {
		pMalicious = probs[1]
	}

	riskScore := pMalicious * 100.0
	return riskScore, feats, nil
}

// scoreRequestFunc allows overriding threat score in tests or runtime
var scoreRequestFunc = func(req *http.Request) int {
	return 0
}

// scoreRequest evaluates request threat score using ONNX model
func scoreRequest(req *http.Request) int {
	// Gate force_score test override behind GATEGUARD_TEST_MODE env var
	if os.Getenv("GATEGUARD_TEST_MODE") == "true" {
		if forceStr := req.URL.Query().Get("force_score"); forceStr != "" {
			if val, err := strconv.Atoi(forceStr); err == nil {
				return val
			}
		}
	}

	// Read and restore request body
	var bodyBytes []byte
	if req.Body != nil {
		bodyBytes, _ = io.ReadAll(req.Body)
		req.Body = io.NopCloser(bytes.NewReader(bodyBytes))
	}

	reqStr := req.URL.RawQuery
	if len(bodyBytes) > 0 {
		if reqStr != "" {
			reqStr += " " + string(bodyBytes)
		} else {
			reqStr = string(bodyBytes)
		}
	}

	if globalEvaluator != nil {
		score, feats, err := globalEvaluator.Score(reqStr)
		if err == nil {
			fmt.Fprintf(os.Stdout, "[ONNX EVAL] Input: %q | Features [entropy=%.4f, len=%.0f, kw=%.0f, special_ratio=%.4f] -> Risk Score: %.2f\n",
				reqStr, feats[0], feats[1], feats[2], feats[3], score)
			return int(math.Round(float64(score)))
		} else {
			log.Printf("[ONNX ERROR] Evaluation failed: %v", err)
		}
	}

	return scoreRequestFunc(req)
}

// statusResponseWriter wraps http.ResponseWriter to capture the HTTP status code.
type statusResponseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (w *statusResponseWriter) WriteHeader(code int) {
	w.statusCode = code
	w.ResponseWriter.WriteHeader(code)
}

func (w *statusResponseWriter) Write(b []byte) (int, error) {
	if w.statusCode == 0 {
		w.statusCode = http.StatusOK
	}
	return w.ResponseWriter.Write(b)
}

// extractSessionToken retrieves bearer token or session_id cookie.
func extractSessionToken(r *http.Request) string {
	authHeader := r.Header.Get("Authorization")
	if strings.HasPrefix(authHeader, "Bearer ") {
		token := strings.TrimSpace(strings.TrimPrefix(authHeader, "Bearer "))
		if token != "" {
			return token
		}
	}

	if cookie, err := r.Cookie("session_id"); err == nil && cookie.Value != "" {
		return cookie.Value
	}

	return ""
}

// hashToken returns the SHA256 hex string of a session token.
func hashToken(token string) string {
	sum := sha256.Sum256([]byte(token))
	return hex.EncodeToString(sum[:])
}

// truncateHash returns the first 8 characters of a SHA256 hash string for display.
func truncateHash(hash string) string {
	if hash == "" {
		return "anon"
	}
	if len(hash) >= 8 {
		return hash[:8]
	}
	return hash
}

// computeCacheKey generates an MD5 hash of (method + path + sorted query params + body).
func computeCacheKey(r *http.Request) (string, error) {
	var bodyBytes []byte
	var err error

	if r.Body != nil {
		bodyBytes, err = io.ReadAll(r.Body)
		if err != nil {
			return "", err
		}
		// Restore r.Body so downstream handlers/proxies can read it
		r.Body = io.NopCloser(bytes.NewReader(bodyBytes))
	}

	method := r.Method
	path := r.URL.Path
	sortedQueryParams := r.URL.Query().Encode()

	raw := fmt.Sprintf("%s|%s|%s|%s", method, path, sortedQueryParams, string(bodyBytes))
	hash := md5.Sum([]byte(raw))
	return hex.EncodeToString(hash[:]), nil
}

// sessionKillMiddleware handles session risk scoring across clean, challenged, suspicious, killed, and blocklisted tiers.
func sessionKillMiddleware(rdb *redis.Client, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		token := extractSessionToken(r)
		tokenHash := ""
		displayHash := "anon"
		if token != "" {
			tokenHash = hashToken(token)
			displayHash = truncateHash(tokenHash)
		}

		ctx := r.Context()
		reqPath := r.URL.RequestURI()
		timestamp := time.Now().Format(time.RFC3339)

		// 1. Blocklist pre-check: Reject immediately if in blocklist SET
		if tokenHash != "" {
			isBlocked, err := rdb.SIsMember(ctx, "blocklist", tokenHash).Result()
			if err == nil && isBlocked {
				fmt.Fprintf(os.Stdout, "[TIER: blocklisted] Token %s is in blocklist, rejecting request without scoring\n", tokenHash)
				globalLogBuffer.Add(LogEntry{
					Timestamp:        timestamp,
					Path:             reqPath,
					SessionTokenHash: displayHash,
					RiskScore:        nil, // Not scored: null in JSON to reflect pre-check rejection
					Tier:             "blocklisted",
					Action:           "rejected_403",
				})

				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusForbidden)
				w.Write([]byte(`{"error":"session_revoked","message":"session revoked"}` + "\n"))
				return
			}
		}

		// 2. Score request & evaluate tiers
		score := scoreRequest(r)

		if score <= RISK_THRESHOLD_LOW {
			// Tier: CLEAN / ALLOW
			fmt.Fprintf(os.Stdout, "[TIER: clean] Session %s score %d <= %d\n", tokenHash, score, RISK_THRESHOLD_LOW)
			globalLogBuffer.Add(LogEntry{
				Timestamp:        timestamp,
				Path:             reqPath,
				SessionTokenHash: displayHash,
				RiskScore:        intPtr(score),
				Tier:             "clean",
				Action:           "forwarded",
			})
			next.ServeHTTP(w, r)
			return
		}

		if score <= RISK_THRESHOLD_HIGH {
			// Tier: CHALLENGE (65 < score <= 85)
			fmt.Fprintf(os.Stdout, "[TIER: challenged] Session %s score %d -> Applying 500ms challenge delay...\n", tokenHash, score)
			time.Sleep(500 * time.Millisecond)

			// Re-validate session token in Redis after delay
			isBlockedNow := false
			if tokenHash != "" {
				isBlockedNow, _ = rdb.SIsMember(ctx, "blocklist", tokenHash).Result()
			}

			if isBlockedNow {
				fmt.Fprintf(os.Stdout, "[TIER: challenged] Session %s re-validation failed (token blocked)\n", tokenHash)
				globalLogBuffer.Add(LogEntry{
					Timestamp:        timestamp,
					Path:             reqPath,
					SessionTokenHash: displayHash,
					RiskScore:        intPtr(score),
					Tier:             "challenged",
					Action:           "rejected_401",
				})

				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusUnauthorized)
				w.Write([]byte(`{"error":"unauthorized","message":"session invalid or expired"}` + "\n"))
				return
			}

			fmt.Fprintf(os.Stdout, "[TIER: challenged] Session %s passed challenge delay successfully\n", tokenHash)
			globalLogBuffer.Add(LogEntry{
				Timestamp:        timestamp,
				Path:             reqPath,
				SessionTokenHash: displayHash,
				RiskScore:        intPtr(score),
				Tier:             "challenged",
				Action:           "forwarded",
			})
			next.ServeHTTP(w, r)
			return
		}

		// Tier: KILL / TWO-STRIKE (score > 85)
		sessionKey := "session:" + tokenHash
		var strikes int64 = 1
		if tokenHash != "" {
			var err error
			strikes, err = rdb.HIncrBy(ctx, sessionKey, "strikes", 1).Result()
			if err != nil {
				log.Printf("[PROXY ERROR] Failed to update Redis strikes: %v", err)
			}
		}

		if strikes == 1 {
			if tokenHash != "" {
				rdb.HSet(ctx, sessionKey, "status", "suspicious")
			}
			fmt.Fprintf(os.Stdout, "[TIER: suspicious] Session %s marked suspicious (Strike 1)\n", tokenHash)
			globalLogBuffer.Add(LogEntry{
				Timestamp:        timestamp,
				Path:             reqPath,
				SessionTokenHash: displayHash,
				RiskScore:        intPtr(score),
				Tier:             "suspicious",
				Action:           "forwarded",
			})
			next.ServeHTTP(w, r)
			return
		}

		if strikes >= 2 {
			if tokenHash != "" {
				rdb.HSet(ctx, sessionKey, "status", "killed")
				rdb.SAdd(ctx, "blocklist", tokenHash)
			}
			fmt.Fprintf(os.Stdout, "[TIER: killed] Session %s got strike %d (killed & blocklisted)\n", tokenHash, strikes)

			globalLogBuffer.Add(LogEntry{
				Timestamp:        timestamp,
				Path:             reqPath,
				SessionTokenHash: displayHash,
				RiskScore:        intPtr(score),
				Tier:             "killed",
				Action:           "rejected_403",
			})

			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"session_killed","message":"session killed due to high risk"}` + "\n"))
			return
		}

		next.ServeHTTP(w, r)
	})
}

// cachePreCheckMiddleware checks LRU cache before scoring and forwarding requests.
func cachePreCheckMiddleware(cache *lru.Cache[string, bool], next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/healthz" || r.URL.Path == "/logs" || r.URL.Path == "/debug/flush-redis" {
			next.ServeHTTP(w, r)
			return
		}

		key, err := computeCacheKey(r)
		if err != nil {
			log.Printf("[PROXY ERROR] Failed to compute cache key: %v", err)
			next.ServeHTTP(w, r)
			return
		}

		if isClean, ok := cache.Get(key); ok && isClean {
			fmt.Fprintf(os.Stdout, "[CACHE HIT] Key: %s | %s %s\n", key, r.Method, r.URL.RequestURI())
			next.ServeHTTP(w, r)
			return
		}

		fmt.Fprintf(os.Stdout, "[CACHE MISS] Key: %s | %s %s\n", key, r.Method, r.URL.RequestURI())

		score := scoreRequest(r)
		// Store in cache only if score is within clean threshold (score <= RISK_THRESHOLD_LOW)
		if score <= RISK_THRESHOLD_LOW {
			cache.Add(key, true)
		}

		next.ServeHTTP(w, r)
	})
}

// loggingMiddleware logs the request method, path, and response status to stdout.
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		wrapped := &statusResponseWriter{
			ResponseWriter: w,
			statusCode:     http.StatusOK,
		}

		next.ServeHTTP(wrapped, r)

		fmt.Fprintf(os.Stdout, "[PROXY LOG] %s %s -> Status: %d\n", r.Method, r.URL.RequestURI(), wrapped.statusCode)
	})
}

func setupServerWithRedis(backendTarget string, rdb *redis.Client) (http.Handler, error) {
	targetURL, err := url.Parse(backendTarget)
	if err != nil {
		return nil, fmt.Errorf("invalid backend URL: %w", err)
	}

	cache, err := lru.New[string, bool](1000)
	if err != nil {
		return nil, fmt.Errorf("failed to create LRU cache: %w", err)
	}

	proxy := httputil.NewSingleHostReverseProxy(targetURL)
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)
		req.Host = targetURL.Host
	}

	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		log.Printf("[PROXY ERROR] Backend connection failed: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway)
		fmt.Fprintf(w, `{"error":"bad_gateway","message":"%s"}`+"\n", err.Error())
	}

	mux := http.NewServeMux()

	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	})

	// GET /logs endpoint with CORS enabled for frontend polling
	mux.HandleFunc("/logs", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		logs := globalLogBuffer.GetLogs()
		json.NewEncoder(w).Encode(logs)
	})

	// POST /debug/flush-redis endpoint to flush all Redis data (gated behind GATEGUARD_TEST_MODE)
	mux.HandleFunc("/debug/flush-redis", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "*")
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		if os.Getenv("GATEGUARD_TEST_MODE") != "true" {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"test_mode_disabled","message":"debug endpoints require GATEGUARD_TEST_MODE=true"}` + "\n"))
			return
		}

		ctx := r.Context()
		if err := rdb.FlushAll(ctx).Err(); err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			fmt.Fprintf(w, `{"error":"flush_failed","message":"%s"}`+"\n", err.Error())
			return
		}

		// Also reset the in-memory log buffer so logs start clean
		globalLogBuffer = NewLogBuffer(100)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok","message":"Redis and log buffer flushed successfully"}` + "\n"))
	})

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		proxy.ServeHTTP(w, r)
	})

	sessionHandler := sessionKillMiddleware(rdb, mux)
	cachedHandler := cachePreCheckMiddleware(cache, sessionHandler)
	loggedHandler := loggingMiddleware(cachedHandler)

	return loggedHandler, nil
}

func initRedisClient() *redis.Client {
	rdb := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
	})

	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Printf("Local Redis server not found on localhost:6379, starting embedded miniredis server...")
		mr := miniredis.NewMiniRedis()
		if mrErr := mr.StartAddr("localhost:6379"); mrErr != nil {
			log.Printf("Failed to start embedded miniredis on localhost:6379: %v", mrErr)
		} else {
			log.Printf("Embedded miniredis started at %s", mr.Addr())
		}
	}

	return rdb
}

func main() {
	backendTarget := "http://localhost:8000"

	// Load ONNX model once at startup
	var err error
	globalEvaluator, err = initONNXModel("models/gateguard_model.onnx")
	if err != nil {
		log.Fatalf("Failed to initialize ONNX model: %v", err)
	}

	rdb := initRedisClient()

	handler, err := setupServerWithRedis(backendTarget, rdb)
	if err != nil {
		log.Fatalf("Server setup failed: %v", err)
	}

	port := ":9000"
	log.Printf("GateGuard Go Reverse Proxy listening on %s (Forwarding -> %s)\n", port, backendTarget)
	if err := http.ListenAndServe(port, handler); err != nil {
		log.Fatalf("Proxy server failed: %v", err)
	}
}
