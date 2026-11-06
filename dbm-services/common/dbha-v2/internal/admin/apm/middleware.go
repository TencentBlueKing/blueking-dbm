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

// metricLabelUnmatched folds every unmatched route into one bounded path label value.
const metricLabelUnmatched = "unmatched"

// allowedHTTPMethods bounds the method label to the standard HTTP methods.
var allowedHTTPMethods = map[string]struct{}{
	http.MethodGet:     {},
	http.MethodPost:    {},
	http.MethodPut:     {},
	http.MethodDelete:  {},
	http.MethodPatch:   {},
	http.MethodHead:    {},
	http.MethodOptions: {},
}

// normalizeHTTPMethod folds unknown HTTP methods into a single bounded label value.
func normalizeHTTPMethod(method string) string {
	if _, ok := allowedHTTPMethods[method]; ok {
		return method
	}
	return metricLabelUnknown
}

// MetricMiddleware returns a gin middleware for collecting API metrics
func MetricMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Excluded paths are judged by the route template for registered routes and
		// by the raw URL for unmatched ones, before the path label is normalized.
		routePath := c.FullPath()
		if isExcludedPath(routePath) || (routePath == "" && isExcludedPath(c.Request.URL.Path)) {
			c.Next()
			return
		}

		method := normalizeHTTPMethod(c.Request.Method)

		// Registered routes expose their route template; unmatched requests are folded
		// into a constant so arbitrary URLs cannot create unbounded series.
		path := routePath
		if path == "" {
			path = metricLabelUnmatched
		}

		start := time.Now()
		reqSize := computeRequestSize(c.Request)

		c.Next()

		durationMs := float64(time.Since(start).Milliseconds())
		status := strconv.Itoa(c.Writer.Status())
		respSize := float64(c.Writer.Size())
		if respSize < 0 {
			respSize = 0
		}
		recordAPIMetrics(method, path, status, durationMs, reqSize, respSize, c.Writer.Status() >= 400)
	}
}

// recordAPIMetrics records all API metrics for one request with the same method/path/status.
func recordAPIMetrics(method, path, status string, durationMs float64, reqSize int, respSize float64, isError bool) {
	l := map[string]string{MetricLabelMethod: method, MetricLabelPath: path}
	lWithStatus := map[string]string{MetricLabelMethod: method, MetricLabelPath: path, MetricLabelStatus: status}

	if err := APIRequestsTotal.IncWithLabels(lWithStatus); err != nil {
		logger.Warn("failed to record api_requests_total, errmsg: %s", err)
	}
	if err := APIRequestDurationMs.ObserveWithLabels(l, durationMs); err != nil {
		logger.Warn("failed to record api_request_duration_ms, errmsg: %s", err)
	}
	if err := APIRequestSizeBytes.ObserveWithLabels(l, float64(reqSize)); err != nil {
		logger.Warn("failed to record api_request_size_bytes, errmsg: %s", err)
	}
	if err := APIResponseSizeBytes.ObserveWithLabels(l, respSize); err != nil {
		logger.Warn("failed to record api_response_size_bytes, errmsg: %s", err)
	}
	if isError {
		if err := APIRequestErrorsTotal.IncWithLabels(l); err != nil {
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
