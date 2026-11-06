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

package apm

import (
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/testutil"
)

func TestHTTPMethodLabelAllowlist(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{in: http.MethodGet, want: http.MethodGet},
		{in: http.MethodPost, want: http.MethodPost},
		{in: http.MethodPut, want: http.MethodPut},
		{in: http.MethodDelete, want: http.MethodDelete},
		{in: http.MethodPatch, want: http.MethodPatch},
		{in: http.MethodHead, want: http.MethodHead},
		{in: http.MethodOptions, want: http.MethodOptions},
		{in: "PURGE", want: metricLabelUnknown},
		{in: "", want: metricLabelUnknown},
	}
	for _, tc := range cases {
		if got := normalizeHTTPMethod(tc.in); got != tc.want {
			t.Fatalf("normalizeHTTPMethod(%q)=%q, want %q", tc.in, got, tc.want)
		}
	}
}

func bindAPITestCollector(t *testing.T) *prometheus.CounterVec {
	t.Helper()
	requests := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "test_api_requests_total", Help: "test",
	}, []string{MetricLabelMethod, MetricLabelPath, MetricLabelStatus})
	prevCollector := APIRequestsTotal.ToMetric().Collector
	APIRequestsTotal.ToMetric().Collector = requests
	t.Cleanup(func() {
		APIRequestsTotal.ToMetric().Collector = prevCollector
	})
	return requests
}

func newMetricTestRouter(t *testing.T, noRoute gin.HandlerFunc) *gin.Engine {
	t.Helper()
	prevMode := gin.Mode()
	gin.SetMode(gin.TestMode)
	t.Cleanup(func() {
		gin.SetMode(prevMode)
	})

	router := gin.New()
	router.Use(MetricMiddleware())
	router.GET("/health", func(c *gin.Context) { c.Status(http.StatusOK) })
	router.GET("/swagger.json", func(c *gin.Context) { c.Status(http.StatusOK) })
	router.GET("/swagger-ui/*any", func(c *gin.Context) { c.Status(http.StatusOK) })
	if noRoute != nil {
		router.NoRoute(noRoute)
	}
	return router
}

func TestMetricMiddlewareUnmatchedPath(t *testing.T) {
	requests := bindAPITestCollector(t)
	noRouteCalled := false
	router := newMetricTestRouter(t, func(c *gin.Context) {
		noRouteCalled = true
		c.Status(http.StatusTeapot)
	})

	req := httptest.NewRequest("FOOBAR", "/any/unregistered/path", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if !noRouteCalled {
		t.Fatal("unmatched request must still reach the NoRoute handler")
	}
	if w.Code != http.StatusTeapot {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusTeapot)
	}
	status := strconv.Itoa(http.StatusTeapot)
	if got := testutil.ToFloat64(requests.WithLabelValues(
		metricLabelUnknown, metricLabelUnmatched, status,
	)); got != 1 {
		t.Fatalf("api_requests_total for unmatched request = %v, want 1", got)
	}
	if got := testutil.CollectAndCount(requests); got != 1 {
		t.Fatalf("unmatched request created %d series, want 1", got)
	}
}

func TestMetricMiddlewareExcludedPaths(t *testing.T) {
	requests := bindAPITestCollector(t)
	router := newMetricTestRouter(t, nil)

	cases := []struct {
		method string
		path   string
	}{
		{http.MethodGet, "/health"},
		{http.MethodPost, "/health"},
		{http.MethodGet, "/metrics"},
		{http.MethodGet, "/swagger.json"},
		{http.MethodGet, "/swagger-ui/index.html"},
	}
	for _, tc := range cases {
		req := httptest.NewRequest(tc.method, tc.path, nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
	if got := testutil.CollectAndCount(requests); got != 0 {
		t.Fatalf("excluded paths created %d series, want 0", got)
	}
}
