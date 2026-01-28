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

		// Calculate metrics after request processing
		latency := float64(time.Since(start).Milliseconds())
		status := strconv.Itoa(c.Writer.Status())
		respSize := float64(c.Writer.Size())
		if respSize < 0 {
			respSize = 0
		}

		// Record request total
		if err := APIRequestsTotal.UpdateLabel(map[string]string{
			MetricLabelMethod: method,
			MetricLabelPath:   path,
			MetricLabelStatus: status,
		}).Inc(); err != nil {
			logger.Warn("failed to record api_requests_total metric, errmsg: %s", err)
		}

		// Record request latency
		if err := APIRequestLatencyMs.UpdateLabel(map[string]string{
			MetricLabelMethod: method,
			MetricLabelPath:   path,
		}).Observe(latency); err != nil {
			logger.Warn("failed to record api_request_latency_ms metric, errmsg: %s", err)
		}

		// Record request size
		if err := APIRequestSizeBytes.UpdateLabel(map[string]string{
			MetricLabelMethod: method,
			MetricLabelPath:   path,
		}).Observe(float64(reqSize)); err != nil {
			logger.Warn("failed to record api_request_size_bytes metric, errmsg: %s", err)
		}

		// Record response size
		if err := APIResponseSizeBytes.UpdateLabel(map[string]string{
			MetricLabelMethod: method,
			MetricLabelPath:   path,
		}).Observe(respSize); err != nil {
			logger.Warn("failed to record api_response_size_bytes metric, errmsg: %s", err)
		}

		// Record errors (status >= 400)
		if c.Writer.Status() >= 400 {
			if err := APIRequestErrorsTotal.UpdateLabel(map[string]string{
				MetricLabelMethod: method,
				MetricLabelPath:   path,
			}).Inc(); err != nil {
				logger.Warn("failed to record api_request_errors_total metric, errmsg: %s", err)
			}
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
