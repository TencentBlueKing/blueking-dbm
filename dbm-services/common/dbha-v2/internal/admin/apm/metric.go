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
	// MetricLabelReason explains why a probe config request could not be answered from the
	// local metadata cache. It is deliberately a small fixed set of values: labelling by ip or
	// bk_cloud_id would create one time series per machine.
	MetricLabelReason = "reason"
)

var (
	APIRequestsTotal      *haapm.HaCounter
	APIRequestDurationMs  *haapm.HaHistogram
	APIRequestSizeBytes   *haapm.HaHistogram
	APIResponseSizeBytes  *haapm.HaHistogram
	APIRequestErrorsTotal *haapm.HaCounter
	// ProbeMetadataFallbackTotal counts probe config requests served from the DBM API instead
	// of the local cache. Probes now ask periodically, so a rise here means admin is amplifying
	// that traffic onto DBM and is the signal to look at metadata sync lag.
	ProbeMetadataFallbackTotal *haapm.HaCounter
)

func init() {
	// API request total counter
	APIRequestsTotal = haapm.NewHaCounter(
		"api_requests_total",
		"Total number of API requests",
		MetricLabelMethod, MetricLabelPath, MetricLabelStatus,
	)

	// API request duration histogram
	APIRequestDurationMs = haapm.NewHaHistogramWithBuckets(
		"api_request_duration_ms",
		"API request duration (milliseconds)",
		haapm.DefaultDurationBuckets,
		MetricLabelMethod, MetricLabelPath,
	)

	// API request size histogram
	APIRequestSizeBytes = haapm.NewHaHistogramWithBuckets(
		"api_request_size_bytes",
		"API request size (bytes)",
		haapm.DefaultSizeBuckets,
		MetricLabelMethod, MetricLabelPath,
	)

	// API response size histogram
	APIResponseSizeBytes = haapm.NewHaHistogramWithBuckets(
		"api_response_size_bytes",
		"API response size (bytes)",
		haapm.DefaultSizeBuckets,
		MetricLabelMethod, MetricLabelPath,
	)

	// API request errors counter
	APIRequestErrorsTotal = haapm.NewHaCounter(
		"api_request_errors_total",
		"Total number of API request errors",
		MetricLabelMethod, MetricLabelPath,
	)

	// Probe metadata cache fallback counter
	ProbeMetadataFallbackTotal = haapm.NewHaCounter(
		"probe_metadata_fallback_total",
		"Total number of probe config requests that fell back to the DBM metadata API",
		MetricLabelReason,
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
		APIRequestDurationMs,
		APIRequestSizeBytes,
		APIResponseSizeBytes,
		APIRequestErrorsTotal,
		ProbeMetadataFallbackTotal,
	)
}
