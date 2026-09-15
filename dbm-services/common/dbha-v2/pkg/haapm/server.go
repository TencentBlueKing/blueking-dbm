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

package haapm

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const (
	defaultMetricsPath = "/metrics"
	defaultHealthPath  = "/health"
)

// ServerConfig configures the haapm metrics HTTP server.
type ServerConfig struct {
	Addr         string        // Listen address, e.g. ":9090"
	Subsystem    string        // Prometheus subsystem (metric name prefix)
	ReadTimeout  time.Duration // Read timeout
	WriteTimeout time.Duration // Write timeout
	MetricsPath  string        // Path for Prometheus scrape; default "/metrics"
	HealthPath   string        // Path for health check; default "/health"
}

// Server exposes Prometheus metrics over HTTP (service registration + port listening).
//
// Option 1 (explicit): NewServer(cfg).Register(m1, m2, ...).RegisterMetrics(apm.Metrics).Start()
type Server struct {
	config  ServerConfig
	metrics []*Metric
	server  *http.Server
	router  *gin.Engine
	mu      sync.Mutex
	wg      sync.WaitGroup
	started bool
}

// NewServer creates a new haapm Server with the given config.
func NewServer(cfg ServerConfig) *Server {
	if cfg.MetricsPath == "" {
		cfg.MetricsPath = defaultMetricsPath
	}
	if cfg.HealthPath == "" {
		cfg.HealthPath = defaultHealthPath
	}
	return &Server{
		config:  cfg,
		metrics: nil,
	}
}

// registerMetric converts a value to *Metric and appends to s.metrics.
// v can be MetricGetter or *Metric.
func (s *Server) registerMetric(v interface{}) error {
	switch m := v.(type) {
	case MetricGetter:
		s.metrics = append(s.metrics, m.ToMetric())
		return nil
	case *Metric:
		s.metrics = append(s.metrics, m)
		return nil
	default:
		return fmt.Errorf("haapm: Register expects MetricGetter or *Metric, got %T", v)
	}
}

// Register adds one or more metrics to the server. Each v can be MetricGetter (e.g. *HaCounter)
// or *Metric. Must be called before Start().
func (s *Server) Register(metrics ...interface{}) *Server {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.started {
		return s
	}
	for _, m := range metrics {
		if err := s.registerMetric(m); err != nil {
			logger.Warn("haapm Register skip metric, errmsg: %s", err)
		}
	}
	return s
}

// RegisterMetrics adds a slice of *Metric to the server. Convenience for apm.Metrics.
func (s *Server) RegisterMetrics(metrics []*Metric) *Server {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.started {
		return s
	}
	for _, m := range metrics {
		if m != nil {
			s.metrics = append(s.metrics, m)
		}
	}
	return s
}

// bindPrometheus creates Prometheus collectors from s.metrics, registers them,
// and assigns Collector back to each metric so Ha* types can use them.
// Idempotent per *Metric object: if m.Collector is already set, that metric is skipped.
// Different Metric objects with the same name still conflict (AlreadyRegisteredError).
func (s *Server) bindPrometheus() error {
	for _, m := range s.metrics {
		if m == nil {
			continue
		}
		if m.Collector != nil {
			continue
		}
		col := newCollector(m, s.config.Subsystem)
		if col == nil {
			return fmt.Errorf("unsupported metric type %s for %s", m.Type, m.Name)
		}
		if err := prometheus.Register(col); err != nil {
			return fmt.Errorf("register metric %s: %w", m.Name, err)
		}
		m.Collector = col
	}
	return nil
}

// Start starts the HTTP server for /metrics (and optionally /health). Non-blocking.
// Bind errors are returned synchronously so hot-replace callers can detect listen failures.
func (s *Server) Start() error {
	s.mu.Lock()
	if s.started {
		s.mu.Unlock()
		return fmt.Errorf("haapm server already started")
	}
	if err := s.bindPrometheus(); err != nil {
		s.mu.Unlock()
		return err
	}
	gin.SetMode(gin.ReleaseMode)
	s.router = gin.New()
	s.router.Use(gin.Recovery())
	s.router.GET(s.config.MetricsPath, gin.WrapH(promhttp.Handler()))
	if s.config.HealthPath != "" {
		s.router.GET(s.config.HealthPath, func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"status": "ok"})
		})
	}
	s.server = &http.Server{
		Addr:         s.config.Addr,
		Handler:      s.router,
		ReadTimeout:  s.config.ReadTimeout,
		WriteTimeout: s.config.WriteTimeout,
	}

	ln, err := net.Listen("tcp", s.config.Addr)
	if err != nil {
		s.router = nil
		s.server = nil
		s.mu.Unlock()
		return fmt.Errorf("listen %s failed: %w", s.config.Addr, err)
	}

	httpSrv := s.server
	addr := s.config.Addr
	s.started = true
	s.wg.Add(1)
	s.mu.Unlock()

	go func() {
		defer s.wg.Done()
		logger.Info("haapm metrics server listening on %s", addr)
		if err := httpSrv.Serve(ln); err != nil && err != http.ErrServerClosed {
			logger.Error("haapm metrics server error, errmsg: %s", err)
		}
	}()
	return nil
}

// Stop shuts down the HTTP server. Collectors stay registered so a later Start
// (or ApplyListenConfig) can reuse them without AlreadyRegisteredError.
func (s *Server) Stop() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.stopLocked()
}

func (s *Server) stopLocked() error {
	if !s.started || s.server == nil {
		s.started = false
		s.server = nil
		s.router = nil
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	err := s.server.Shutdown(ctx)
	s.started = false
	s.server = nil
	s.router = nil
	// Wait outside holding semantics: Shutdown unblocks Serve; wait for goroutine exit.
	s.mu.Unlock()
	s.wg.Wait()
	s.mu.Lock()
	return err
}

// ApplyListenConfig updates listen-related fields and restarts the HTTP server
// without rebinding Prometheus collectors. Subsystem is preserved from the first
// successful bind so hot-replace of the metrics address stays idempotent.
func (s *Server) ApplyListenConfig(cfg ServerConfig) error {
	if cfg.MetricsPath == "" {
		cfg.MetricsPath = defaultMetricsPath
	}
	if cfg.HealthPath == "" {
		cfg.HealthPath = defaultHealthPath
	}

	s.mu.Lock()
	if err := s.stopLocked(); err != nil {
		s.mu.Unlock()
		return err
	}
	subsystem := s.config.Subsystem
	s.config = cfg
	if s.config.Subsystem == "" {
		s.config.Subsystem = subsystem
	}
	s.mu.Unlock()

	return s.Start()
}
