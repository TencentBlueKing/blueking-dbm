/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package hanet

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"golang.org/x/time/rate"
)

// TestGinHTTPServer_Basic basic functionality test
func TestGinHTTPServer_Basic(t *testing.T) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8081,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)

	// Setup routes and middlewares first
	server.setupMiddlewares()
	server.setupRoutes()

	// Test health check without starting actual server
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	// Test server startup and stop in a goroutine to avoid blocking
	done := make(chan bool)
	go func() {
		// Test server startup
		if err := server.Start(); err != nil {
			t.Errorf("Failed to start server: %v", err)
			done <- false
			return
		}

		// Give server time to start
		time.Sleep(100 * time.Millisecond)

		// Test server stop
		if err := server.Stop(); err != nil {
			t.Errorf("Failed to stop server: %v", err)
			done <- false
			return
		}

		done <- true
	}()

	// Wait for test completion with timeout
	select {
	case success := <-done:
		if !success {
			t.Fatal("Server test failed")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Server test timed out")
	}
}

// TestGinHTTPServer_Auth authentication functionality test
func TestGinHTTPServer_Auth(t *testing.T) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8082,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)
	server.SetAuthHandler(&testAuthHandler{})

	// Setup routes and middlewares
	server.setupMiddlewares()
	server.setupRoutes()

	// Test unauthorized access (no Authorization header)
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401 for unauthorized access, got %d", w.Code)
	}

	// Test unauthorized access (invalid token)
	req = httptest.NewRequest("GET", "/health", nil)
	req.Header.Set("Authorization", "Bearer invalid-token")
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401 for invalid token, got %d", w.Code)
	}

	// Test authorized access
	req = httptest.NewRequest("GET", "/health", nil)
	req.Header.Set("Authorization", "Bearer valid-token")
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200 for authorized access, got %d", w.Code)
	}
}

// TestGinHTTPServer_RateLimit rate limiting functionality test
func TestGinHTTPServer_RateLimit(t *testing.T) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8083,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)
	server.SetRateLimit(&RateLimitConfig{
		Enabled: true,
		Rate:    rate.Limit(1), // 1 request per second
		Burst:   1,
	})

	// Setup routes and middlewares
	server.setupMiddlewares()
	server.setupRoutes()

	// First request should succeed
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("First request should succeed, got status %d", w.Code)
	}

	// Second request should be rate limited
	req = httptest.NewRequest("GET", "/health", nil)
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusTooManyRequests {
		t.Errorf("Second request should be rate limited, got status %d", w.Code)
	}
}

// TestGinHTTPServer_ResetAPI reset API functionality test
func TestGinHTTPServer_ResetAPI(t *testing.T) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8084,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)
	server.RegisterAPI(&ResetAPI{
		Method: HttpMethod("POST"),
		Path:   "/api/reset",
		Handler: func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{
				"message": "reset successful",
			})
		},
	})

	// Setup routes and middlewares
	server.setupMiddlewares()
	server.setupRoutes()

	// Test reset API
	req := httptest.NewRequest("POST", "/api/reset", nil)
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200 for reset API, got %d", w.Code)
	}

	if !strings.Contains(w.Body.String(), "reset successful") {
		t.Errorf("Response should contain reset message, got: %s", w.Body.String())
	}
}

// TestGinHTTPServer_IPWhitelist IP whitelist functionality test
func TestGinHTTPServer_IPWhitelist(t *testing.T) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8085,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)
	server.SetRateLimit(&RateLimitConfig{
		Enabled:     true,
		Rate:        rate.Limit(0.1), // Very strict rate limit: 1 request per 10 seconds
		Burst:       0,
		IPWhitelist: []string{"127.0.0.1"},
	})

	// Setup routes and middlewares
	server.setupMiddlewares()
	server.setupRoutes()

	// Whitelisted IP should not be rate limited
	req := httptest.NewRequest("GET", "/health", nil)
	req.RemoteAddr = "127.0.0.1:12345"
	w := httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Whitelisted IP should not be rate limited, got status %d", w.Code)
	}

	// Second request from whitelisted IP should still succeed
	req = httptest.NewRequest("GET", "/health", nil)
	req.RemoteAddr = "127.0.0.1:12345"
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Whitelisted IP should not be rate limited on second request, got status %d", w.Code)
	}

	// Test non-whitelisted IP should be rate limited on first request
	req = httptest.NewRequest("GET", "/health", nil)
	req.Header.Set("X-Forwarded-For", "127.0.0.2")
	req.RemoteAddr = "127.0.0.2:12345"
	w = httptest.NewRecorder()
	server.router.ServeHTTP(w, req)

	if w.Code != http.StatusTooManyRequests {
		t.Errorf("Non-whitelisted IP should be rate limited on first request, got status %d", w.Code)
	}
}

// TestGinHTTPServer_DoubleStart double start functionality test
func TestGinHTTPServer_DoubleStart(t *testing.T) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8086,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)

	// First start should succeed
	if err := server.Start(); err != nil {
		t.Fatalf("First start should succeed: %v", err)
	}

	// Second start should fail
	if err := server.Start(); err == nil {
		t.Error("Second start should fail")
	}

	// Stop the server
	if err := server.Stop(); err != nil {
		t.Fatalf("Failed to stop server: %v", err)
	}
}

// TestGinHTTPServer_DoubleStop double stop functionality test
func TestGinHTTPServer_DoubleStop(t *testing.T) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8087,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)

	// Start the server
	if err := server.Start(); err != nil {
		t.Fatalf("Failed to start server: %v", err)
	}

	// First stop should succeed
	if err := server.Stop(); err != nil {
		t.Fatalf("First stop should succeed: %v", err)
	}

	// Second stop should fail
	if err := server.Stop(); err == nil {
		t.Error("Second stop should fail")
	}
}

// TestGinHTTPServer_CustomLogger custom logger functionality test
func TestGinHTTPServer_CustomLogger(t *testing.T) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8088,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)

	// Setup routes and middlewares
	server.setupMiddlewares()
	server.setupRoutes()

	// Test request logging with different HTTP methods and paths
	testCases := []struct {
		method string
		path   string
	}{
		{"GET", "/health"},
		{"POST", "/api/test"},
		{"PUT", "/api/resource/1"},
		{"DELETE", "/api/resource/1"},
	}

	for _, tc := range testCases {
		req := httptest.NewRequest(tc.method, tc.path, nil)
		w := httptest.NewRecorder()
		server.router.ServeHTTP(w, req)

		// For non-existent routes, expect 404
		if tc.path != "/health" {
			if w.Code != http.StatusNotFound {
				t.Errorf("Expected status 404 for %s %s, got %d", tc.method, tc.path, w.Code)
			}
		} else {
			if w.Code != http.StatusOK {
				t.Errorf("Expected status 200 for %s %s, got %d", tc.method, tc.path, w.Code)
			}
		}
	}
}

// testAuthHandler authentication handler for testing
type testAuthHandler struct{}

func (h *testAuthHandler) Authenticate(c *gin.Context) bool {
	authHeader := c.GetHeader("Authorization")
	return authHeader == "Bearer valid-token"
}

// BenchmarkGinHTTPServer_Performance performance benchmark test
func BenchmarkGinHTTPServer_Performance(b *testing.B) {
	config := &GinServerConfig{
		Host:         "localhost",
		Port:         8089,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	server := NewGinHTTPServer(config)

	// Setup routes and middlewares
	server.setupMiddlewares()
	server.setupRoutes()

	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			req := httptest.NewRequest("GET", "/health", nil)
			w := httptest.NewRecorder()
			server.router.ServeHTTP(w, req)

			if w.Code != http.StatusOK {
				b.Errorf("Expected status 200, got %d", w.Code)
			}
		}
	})
}
