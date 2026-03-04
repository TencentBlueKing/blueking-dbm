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

import "sync"

// defaultRegistry holds metrics registered via MustRegister (Option 2).
var (
	defaultRegistryMu sync.Mutex
	defaultRegistry   []interface{} // MetricGetter or *Metric
)

// MustRegister adds metrics to the global registry (Option 2). Each v can be MetricGetter
// (e.g. *HaCounter, *HaGauge) or *Metric. Call Serve(cfg) later to start the server
// with all registered metrics.
func MustRegister(metrics ...interface{}) {
	defaultRegistryMu.Lock()
	defer defaultRegistryMu.Unlock()
	for _, m := range metrics {
		switch m.(type) {
		case MetricGetter, *Metric:
			defaultRegistry = append(defaultRegistry, m)
		default:
			// skip invalid type
			continue
		}
	}
}

// RegistryMetrics returns a copy of the default registry entries (for use by Serve).
func RegistryMetrics() []interface{} {
	defaultRegistryMu.Lock()
	defer defaultRegistryMu.Unlock()
	out := make([]interface{}, len(defaultRegistry))
	copy(out, defaultRegistry)
	return out
}

// Serve starts a metrics HTTP server using the global registry (Option 2).
// It creates a Server, registers all metrics from MustRegister, and starts listening.
// Non-blocking; returns the *Server so the caller can call Stop() on shutdown.
func Serve(cfg ServerConfig) (*Server, error) {
	svr := NewServer(cfg)
	for _, m := range RegistryMetrics() {
		svr.Register(m)
	}
	if err := svr.Start(); err != nil {
		return nil, err
	}
	return svr, nil
}
