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
	"dbm-services/common/dbha-v2/pkg/haapm"
)

const (
	MetricLabelMethod = "method"
	MetricLabelPath   = "path"
	MetricLabelStatus = "status"
)

var (
	APIRequestsTotal      *haapm.HaCounter
	APIRequestLatencyMs   *haapm.HaHistogram
	APIRequestSizeBytes   *haapm.HaHistogram
	APIResponseSizeBytes  *haapm.HaHistogram
	APIRequestErrorsTotal *haapm.HaCounter
)

// Default histogram buckets for latency (milliseconds)
var defaultLatencyBuckets = []float64{1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000}

// Default histogram buckets for size (bytes)
var defaultSizeBuckets = []float64{100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000}

func init() {
	// API request total counter
	APIRequestsTotal = haapm.NewHaCounter(
		"api_requests_total",
		"Total number of API requests",
		MetricLabelMethod, MetricLabelPath, MetricLabelStatus,
	)

	// API request latency histogram
	APIRequestLatencyMs = haapm.NewHaHistogramWithBuckets(
		"api_request_latency_ms",
		"API request latency (milliseconds)",
		defaultLatencyBuckets,
		MetricLabelMethod, MetricLabelPath,
	)

	// API request size histogram
	APIRequestSizeBytes = haapm.NewHaHistogramWithBuckets(
		"api_request_size_bytes",
		"API request size (bytes)",
		defaultSizeBuckets,
		MetricLabelMethod, MetricLabelPath,
	)

	// API response size histogram
	APIResponseSizeBytes = haapm.NewHaHistogramWithBuckets(
		"api_response_size_bytes",
		"API response size (bytes)",
		defaultSizeBuckets,
		MetricLabelMethod, MetricLabelPath,
	)

	// API request errors counter
	APIRequestErrorsTotal = haapm.NewHaCounter(
		"api_request_errors_total",
		"Total number of API request errors",
		MetricLabelMethod, MetricLabelPath,
	)
}

// InitAPM sets service labels for startup metric and registers all metrics to haapm (Option 2).
// Must be called before haapm.Serve so metrics are collected automatically.
func InitAPM(serviceID, serviceName string) {

	haapm.AppStartupMetric.UpdateLabel(map[string]string{
		haapm.MetricLabelServiceID:   serviceID,
		haapm.MetricLabelServiceName: serviceName,
	})

	haapm.MustRegister(
		haapm.AppStartupMetric,
		APIRequestsTotal,
		APIRequestLatencyMs,
		APIRequestSizeBytes,
		APIResponseSizeBytes,
		APIRequestErrorsTotal,
	)
}
