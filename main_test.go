package main

import (
	"bytes"
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
)

func TestLRUCachePreCheck(t *testing.T) {
	os.Setenv("GATEGUARD_TEST_MODE", "true")
	defer os.Unsetenv("GATEGUARD_TEST_MODE")

	oldScoreFunc := scoreRequestFunc
	scoreRequestFunc = func(req *http.Request) int {
		return 0
	}
	defer func() { scoreRequestFunc = oldScoreFunc }()

	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	defer rdb.Close()

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"success"}`))
	}))
	defer backend.Close()

	proxyHandler, err := setupServerWithRedis(backend.URL, rdb)
	if err != nil {
		t.Fatalf("Failed to setup proxy server: %v", err)
	}

	oldStdout := os.Stdout
	rReader, wWriter, _ := os.Pipe()
	os.Stdout = wWriter

	reqBody := `{"query": "test_search"}`
	req1 := httptest.NewRequest("POST", "/search?b=2&a=1", strings.NewReader(reqBody))
	rec1 := httptest.NewRecorder()
	proxyHandler.ServeHTTP(rec1, req1)

	req2 := httptest.NewRequest("POST", "/search?a=1&b=2", strings.NewReader(reqBody))
	rec2 := httptest.NewRecorder()
	proxyHandler.ServeHTTP(rec2, req2)

	wWriter.Close()
	os.Stdout = oldStdout
	var buf bytes.Buffer
	io.Copy(&buf, rReader)
	logOutput := buf.String()

	if !strings.Contains(logOutput, "CACHE MISS") || !strings.Contains(logOutput, "CACHE HIT") {
		t.Errorf("Expected CACHE MISS and CACHE HIT in logs, got:\n%s", logOutput)
	}
}

func TestTwoStrikeSessionKill(t *testing.T) {
	os.Setenv("GATEGUARD_TEST_MODE", "true")
	defer os.Unsetenv("GATEGUARD_TEST_MODE")

	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	defer rdb.Close()

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	}))
	defer backend.Close()

	oldScoreFunc := scoreRequestFunc
	scoreRequestFunc = func(req *http.Request) int {
		return 90
	}
	defer func() { scoreRequestFunc = oldScoreFunc }()

	proxyHandler, err := setupServerWithRedis(backend.URL, rdb)
	if err != nil {
		t.Fatalf("Failed to setup proxy server: %v", err)
	}

	oldStdout := os.Stdout
	rReader, wWriter, _ := os.Pipe()
	os.Stdout = wWriter

	fakeToken := "fake-bearer-token-12345"

	// Request 1: Strike 1 (Score 90 > 85) -> Allowed & marked suspicious
	req1 := httptest.NewRequest("GET", "/search?q=test1", nil)
	req1.Header.Set("Authorization", "Bearer "+fakeToken)
	rec1 := httptest.NewRecorder()
	proxyHandler.ServeHTTP(rec1, req1)

	if rec1.Code != http.StatusOK {
		t.Errorf("Request 1 expected status 200 OK, got %d", rec1.Code)
	}

	tokenHash := hashToken(fakeToken)
	sessionKey := "session:" + tokenHash
	status1, _ := rdb.HGet(context.Background(), sessionKey, "status").Result()
	strikes1, _ := rdb.HGet(context.Background(), sessionKey, "strikes").Result()
	if status1 != "suspicious" || strikes1 != "1" {
		t.Errorf("Expected status='suspicious' and strikes='1', got status='%s', strikes='%s'", status1, strikes1)
	}

	// Request 2: Strike 2 (Score 90 > 85) -> Rejected with 403 & blocklisted
	req2 := httptest.NewRequest("GET", "/search?q=test2", nil)
	req2.Header.Set("Authorization", "Bearer "+fakeToken)
	rec2 := httptest.NewRecorder()
	proxyHandler.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusForbidden {
		t.Errorf("Request 2 expected status 403 Forbidden, got %d", rec2.Code)
	}

	status2, _ := rdb.HGet(context.Background(), sessionKey, "status").Result()
	isBlocked, _ := rdb.SIsMember(context.Background(), "blocklist", tokenHash).Result()
	if status2 != "killed" || !isBlocked {
		t.Errorf("Expected status='killed' and isBlocked=true, got status='%s', isBlocked=%v", status2, isBlocked)
	}

	// Request 3: Blocklist pre-check -> Rejected with 403 Forbidden immediately
	req3 := httptest.NewRequest("GET", "/search?q=test3", nil)
	req3.Header.Set("Authorization", "Bearer "+fakeToken)
	rec3 := httptest.NewRecorder()
	proxyHandler.ServeHTTP(rec3, req3)

	if rec3.Code != http.StatusForbidden {
		t.Errorf("Request 3 expected status 403 Forbidden (blocklisted), got %d", rec3.Code)
	}

	wWriter.Close()
	os.Stdout = oldStdout
	var buf bytes.Buffer
	io.Copy(&buf, rReader)
	logOutput := buf.String()

	t.Logf("Captured Proxy Logs:\n%s", logOutput)
}

func TestChallengeTier(t *testing.T) {
	os.Setenv("GATEGUARD_TEST_MODE", "true")
	defer os.Unsetenv("GATEGUARD_TEST_MODE")

	mr := miniredis.RunT(t)
	rdb := redis.NewClient(&redis.Options{Addr: mr.Addr()})
	defer rdb.Close()

	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	}))
	defer backend.Close()

	proxyHandler, err := setupServerWithRedis(backend.URL, rdb)
	if err != nil {
		t.Fatalf("Failed to setup proxy server: %v", err)
	}

	fakeToken := "challenge-test-token"
	req := httptest.NewRequest("GET", "/search?q=challenge&force_score=75", nil)
	req.Header.Set("Authorization", "Bearer "+fakeToken)
	rec := httptest.NewRecorder()

	start := time.Now()
	proxyHandler.ServeHTTP(rec, req)
	elapsed := time.Since(start)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200 OK for challenge tier, got %d", rec.Code)
	}
	if elapsed < 500*time.Millisecond {
		t.Errorf("Expected challenge delay of >= 500ms, got %v", elapsed)
	}
}
