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
func (s *Server) bindPrometheus() error {
	for _, m := range s.metrics {
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
	s.started = true
	s.mu.Unlock()

	go func() {
		logger.Info("haapm metrics server listening on %s", s.config.Addr)
		if err := s.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("haapm metrics server error: %v", err)
		}
	}()
	return nil
}

// Stop shuts down the HTTP server.
func (s *Server) Stop() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.started || s.server == nil {
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	err := s.server.Shutdown(ctx)
	if err != nil {
		return err
	}
	s.started = false
	s.server = nil
	s.router = nil
	return nil
}
