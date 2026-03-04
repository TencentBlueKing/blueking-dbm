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
	"strconv"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/gin-gonic/gin"
)

// excludedPaths defines paths that should be excluded from metric collection
var excludedPaths = map[string]bool{
	"/health":          true,
	"/metrics":         true,
	"/swagger-ui":      true,
	"/swagger-ui/*any": true,
	"/swagger.json":    true,
}

// MetricMiddleware returns a gin middleware for collecting API metrics
func MetricMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		method := c.Request.Method

		// This avoids high cardinality issues in metrics
		path := c.FullPath()
		if path == "" {
			// Fallback to raw path if FullPath is empty (e.g., 404 routes)
			path = c.Request.URL.Path
		}

		// Skip excluded paths
		if isExcludedPath(path) {
			c.Next()
			return
		}

		start := time.Now()
		reqSize := computeRequestSize(c.Request)

		c.Next()

		latencyMs := float64(time.Since(start).Milliseconds())
		status := strconv.Itoa(c.Writer.Status())
		respSize := float64(c.Writer.Size())
		if respSize < 0 {
			respSize = 0
		}
		recordAPIMetrics(method, path, status, latencyMs, reqSize, respSize, c.Writer.Status() >= 400)
	}
}

// recordAPIMetrics records all API metrics for one request with the same method/path/status.
func recordAPIMetrics(method, path, status string, latencyMs float64, reqSize int, respSize float64, isError bool) {
	l := map[string]string{MetricLabelMethod: method, MetricLabelPath: path}
	lWithStatus := map[string]string{MetricLabelMethod: method, MetricLabelPath: path, MetricLabelStatus: status}

	if err := APIRequestsTotal.UpdateLabel(lWithStatus).Inc(); err != nil {
		logger.Warn("failed to record api_requests_total, errmsg: %s", err)
	}
	if err := APIRequestLatencyMs.UpdateLabel(l).Observe(latencyMs); err != nil {
		logger.Warn("failed to record api_request_latency_ms, errmsg: %s", err)
	}
	if err := APIRequestSizeBytes.UpdateLabel(l).Observe(float64(reqSize)); err != nil {
		logger.Warn("failed to record api_request_size_bytes, errmsg: %s", err)
	}
	if err := APIResponseSizeBytes.UpdateLabel(l).Observe(respSize); err != nil {
		logger.Warn("failed to record api_response_size_bytes, errmsg: %s", err)
	}
	if isError {
		if err := APIRequestErrorsTotal.UpdateLabel(l).Inc(); err != nil {
			logger.Warn("failed to record api_request_errors_total, errmsg: %s", err)
		}
	}
}

// isExcludedPath checks if the path should be excluded from metric collection
func isExcludedPath(path string) bool {
	if _, ok := excludedPaths[path]; ok {
		return true
	}
	return false
}

// computeRequestSize computes the approximate request size
func computeRequestSize(r *http.Request) int {
	size := 0
	if r.URL != nil {
		size += len(r.URL.Path)
	}

	size += len(r.Method)
	size += len(r.Proto)

	for name, values := range r.Header {
		size += len(name)
		for _, value := range values {
			size += len(value)
		}
	}

	size += len(r.Host)

	if r.ContentLength != -1 {
		size += int(r.ContentLength)
	}

	return size
}
