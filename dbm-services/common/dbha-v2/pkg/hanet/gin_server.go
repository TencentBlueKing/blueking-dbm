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
	"context"
	"fmt"
	"net/http"
	"slices"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/gin-gonic/gin"
	"golang.org/x/time/rate"
)

// GinServerConfig server configuration
type GinServerConfig struct {
	Host         string        // Server host address
	Port         int           // Server port
	ReadTimeout  time.Duration // Read timeout
	WriteTimeout time.Duration // Write timeout
}

// AuthHandler authentication handler interface
type AuthHandler interface {
	Authenticate(c *gin.Context) bool
}

// RateLimitConfig rate limiting configuration
type RateLimitConfig struct {
	Enabled     bool       // Whether to enable rate limiting
	Rate        rate.Limit // Requests per second allowed
	Burst       int        // Burst requests allowed
	IPWhitelist []string   // IP whitelist
}

// ResetAPI reset API configuration
type ResetAPI struct {
	Group   string
	Method  HttpMethod
	Path    string          // API path
	Handler gin.HandlerFunc // Handler function
}

// GinHTTPServer Gin HTTP server implementation
type GinHTTPServer struct {
	config      *GinServerConfig
	authHandler AuthHandler
	rateLimit   *RateLimitConfig
	resetAPIs   []*ResetAPI
	server      *http.Server
	router      *gin.Engine
	mu          sync.RWMutex
	wg          sync.WaitGroup
	started     bool
}

// NewGinHTTPServer creates a new Gin HTTP server
func NewGinHTTPServer(config *GinServerConfig) *GinHTTPServer {
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()

	return &GinHTTPServer{
		config: config,
		router: router,
		server: &http.Server{
			Addr:         fmt.Sprintf("%s:%d", config.Host, config.Port),
			Handler:      router,
			ReadTimeout:  config.ReadTimeout,
			WriteTimeout: config.WriteTimeout,
		},
	}
}

// SetAuthHandler sets authentication handler
func (s *GinHTTPServer) SetAuthHandler(authHandler AuthHandler) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.authHandler = authHandler
}

// SetRateLimit sets rate limiting configuration
func (s *GinHTTPServer) SetRateLimit(rateLimit *RateLimitConfig) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.rateLimit = rateLimit
}

// RegisterAPI register reset API
func (s *GinHTTPServer) RegisterAPI(resetAPI *ResetAPI) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.resetAPIs = append(s.resetAPIs, resetAPI)
}

// Start starts the HTTP server
func (s *GinHTTPServer) Start() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.started {
		return fmt.Errorf("server already started")
	}

	// Setup middlewares
	s.setupMiddlewares()

	// Setup routes
	s.setupRoutes()

	// Start the server
	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		logger.Info("Starting HTTP server on %s", s.server.Addr)
		if err := s.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("Failed to start server: %v", err)
		}
	}()

	s.started = true
	return nil
}

// Stop stops the HTTP server
func (s *GinHTTPServer) Stop() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.started {
		return fmt.Errorf("server not started")
	}

	logger.Info("Stopping HTTP server")

	// Create timeout context
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := s.server.Shutdown(ctx); err != nil {
		logger.Error("Server shutdown error: %v", err)
		return err
	}

	// Wait for goroutines to complete
	s.wg.Wait()
	s.started = false
	logger.Info("HTTP server stopped successfully")
	return nil
}

// setupMiddlewares sets up middlewares
func (s *GinHTTPServer) setupMiddlewares() {
	// Recovery middleware
	s.router.Use(gin.Recovery())

	// Logging middleware
	s.router.Use(s.loggingMiddleware())

	// Rate limiting middleware
	if s.rateLimit != nil && s.rateLimit.Enabled {
		s.router.Use(s.rateLimitMiddleware())
	}

	// Authentication middleware
	if s.authHandler != nil {
		s.router.Use(s.authMiddleware())
	}
}

// setupRoutes sets up routes
func (s *GinHTTPServer) setupRoutes() {
	groupAPIs := map[string]*gin.RouterGroup{}

	// register API routes
	for _, resetAPI := range s.resetAPIs {
		if resetAPI.Group == "" {
			if !s.isRouteRegistered(s.router, string(resetAPI.Method), resetAPI.Path) {
				continue
			}

			s.router.Handle(string(resetAPI.Method), resetAPI.Path, resetAPI.Handler)
			continue
		}

		if _, ok := groupAPIs[resetAPI.Group]; !ok {
			groupAPIs[resetAPI.Group] = s.router.Group(resetAPI.Group)
		}

		if !s.isRouteRegistered(s.router, string(resetAPI.Method), resetAPI.Path) {
			continue
		}

		groupAPIs[resetAPI.Group].Handle(string(resetAPI.Method), resetAPI.Path, resetAPI.Handler)
	}

	// Health check route
	if !s.isRouteRegistered(s.router, "GET", "/health") {
		s.router.Handle("GET", "/health", s.healthHandler)
	}
}

// loggingMiddleware logging middleware
func (s *GinHTTPServer) loggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path

		c.Next()

		latency := time.Since(start)
		status := c.Writer.Status()

		logger.Info("HTTP %s %s %d %s",
			c.Request.Method, path, status, latency)
	}
}

// rateLimitMiddleware rate limiting middleware
func (s *GinHTTPServer) rateLimitMiddleware() gin.HandlerFunc {
	// Create a map to store limiters per IP
	limiters := make(map[string]*rate.Limiter)
	var mu sync.Mutex

	return func(c *gin.Context) {
		clientIP := c.ClientIP()

		// Check IP whitelist
		if slices.Contains(s.rateLimit.IPWhitelist, clientIP) {
			c.Next()
			return
		}

		// Get or create limiter for this IP
		mu.Lock()
		limiter, exists := limiters[clientIP]
		if !exists {
			limiter = rate.NewLimiter(s.rateLimit.Rate, s.rateLimit.Burst)
			limiters[clientIP] = limiter
		}
		mu.Unlock()

		// Apply rate limiting
		if !limiter.Allow() {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error": "rate limit exceeded",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// authMiddleware authentication middleware
func (s *GinHTTPServer) authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		if !s.authHandler.Authenticate(c) {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "unauthorized",
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

// healthHandler health check handler
func (s *GinHTTPServer) healthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":    "healthy",
		"timestamp": time.Now().Unix(),
	})
}

func (s *GinHTTPServer) isRouteRegistered(engine *gin.Engine, method, path string) bool {
	for _, route := range engine.Routes() {
		if route.Method == method && route.Path == path {
			return true
		}
	}

	return false
}
