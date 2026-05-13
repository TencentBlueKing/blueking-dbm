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

// Package keepalive provides a lightweight HTTP ping endpoint for probe process liveness checks.
package keepalive

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	pingPath            = "/ping"
	pingResponse        = "pong"
	defaultCloseTimeout = 5 * time.Second
)

// PingServer serves GET /ping and responds with a fixed "pong" body.
type PingServer struct {
	addr     string
	server   *http.Server
	listener net.Listener
	mu       sync.RWMutex
}

// NewPingServer creates a ping HTTP server bound to the provided listen address.
func NewPingServer(addr string) *PingServer {
	mux := http.NewServeMux()
	mux.HandleFunc(pingPath, pingHandler)

	return &PingServer{
		addr: addr,
		server: &http.Server{
			Addr:    addr,
			Handler: mux,
		},
	}
}

// Addr returns the actual server listen address after Start is called.
func (s *PingServer) Addr() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.listener == nil {
		return s.addr
	}
	return s.listener.Addr().String()
}

// Start binds and starts the ping HTTP server.
func (s *PingServer) Start() error {
	ln, err := net.Listen("tcp", s.addr)
	if err != nil {
		return fmt.Errorf("listen ping http server failed, errmsg: %w", err)
	}

	s.mu.Lock()
	s.listener = ln
	s.mu.Unlock()

	go func() {
		logger.Info("ping http server started, listen_address: %s", s.Addr())
		if err := s.server.Serve(ln); err != nil && err != http.ErrServerClosed {
			logger.Error("ping http server stopped unexpectedly, listen_address: %s, errmsg: %s", s.Addr(), err)
		}
	}()

	return nil
}

// Close gracefully shuts down the ping HTTP server.
func (s *PingServer) Close() error {
	ctx, cancel := context.WithTimeout(context.Background(), defaultCloseTimeout)
	defer cancel()

	if err := s.server.Shutdown(ctx); err != nil {
		return fmt.Errorf("shutdown ping http server failed, errmsg: %w", err)
	}
	return nil
}

func pingHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(pingResponse))
}
