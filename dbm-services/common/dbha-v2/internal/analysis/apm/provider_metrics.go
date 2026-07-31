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
	"fmt"
	"reflect"
	"sort"
	"sync"

	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	dbMetricsMu      sync.RWMutex
	dbMetricsByName  = map[string]struct{}{}
	dbMetricsOrdered []interface{}
	dbMetricsDbTypes = map[haprobe.DbType]struct{}{}
)

// frameworkMetrics returns analysis framework-owned metrics.
// Always returns a fresh slice so callers may append without aliasing shared storage.
func frameworkMetrics() []interface{} {
	return []interface{}{
		haapm.AppStartupMetric,
		PopSwitchBusinessTotal,
		PopSwitchTimeConsumingMs,
		ScanBusinessTimeConsumingMs,
		ScanBusinessTotal,
		SlidingWindowSize,
		AmBusinessTotal,
		TriggerSwitchingInstanceTotal,
		SwitchingInstanceErrorTotal,
		SwitchingInstanceSuccessTotal,
		SwitchingTimeConsumingMs,
		DbQueryTimeConsumingMs,
		DbQueryErrorTotal,
		ThirdPartyApiRequestTimeConsumingMs,
		ThirdPartyApiRequestErrorTotal,
		DbmApiSyncMetadataTotal,
		DbmApiSyncMetadataTimeConsumingMs,
		DbmApiSyncMetadataErrorTotal,
		DbmApiQueryMetadataTimeConsumingMs,
		DbmApiQueryMetadataErrorTotal,
		DbmApiQueryMetadataIpCount,
		DetectorSshTimeConsumingMs,
		DetectorSshErrorTotal,
		DbmMetadataSaveTimeConsumingMs,
		DbmMetadataUpdatedCount,
		DbhaDataStatusUpdatedCount,
	}
}

// FrameworkMetricNames returns framework-owned metric names in sorted order.
// Exported so that packages linking both apm and the providers can assert the
// framework and provider metric name sets never intersect.
func FrameworkMetricNames() []string {
	fw := frameworkMetrics()
	names := make([]string, 0, len(fw))
	seen := map[string]struct{}{}
	for i, m := range fw {
		name, err := metricName(m)
		if err != nil {
			panic(fmt.Sprintf("apm: framework metric at index %d invalid, errmsg: %s", i, err))
		}
		if _, ok := seen[name]; ok {
			continue
		}
		seen[name] = struct{}{}
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func metricName(m interface{}) (string, error) {
	if m == nil {
		return "", fmt.Errorf("nil metric")
	}
	rv := reflect.ValueOf(m)
	if rv.Kind() == reflect.Ptr && rv.IsNil() {
		return "", fmt.Errorf("nil metric pointer of type %T", m)
	}
	switch v := m.(type) {
	case haapm.MetricGetter:
		metric := v.ToMetric()
		if metric == nil {
			return "", fmt.Errorf("MetricGetter.ToMetric returned nil for type %T", m)
		}
		if metric.Name == "" {
			return "", fmt.Errorf("empty metric name for type %T", m)
		}
		return metric.Name, nil
	case *haapm.Metric:
		if v.Name == "" {
			return "", fmt.Errorf("empty metric name for *haapm.Metric")
		}
		return v.Name, nil
	default:
		return "", fmt.Errorf("unsupported metric type %T", m)
	}
}

// RegisterDbMetrics records metrics owned by one DbType provider so that InitAPM
// registers them together with the framework metrics. Intended to be called from
// provider init().
//
// Panics on an invalid DbType, a nil/unsupported metric, a name that collides with
// a framework metric, or a name already registered by another provider. Colliding
// names would otherwise fail prometheus.Register at haapm.Serve time and take the
// whole service down, so they are rejected at init instead.
//
// Validation completes for the full batch before any write; panic leaves global
// state unchanged.
func RegisterDbMetrics(dt haprobe.DbType, metrics ...interface{}) {
	if dt == haprobe.DbTypeNone || dt == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("apm: refuse to register db metrics for invalid DbType: %q", dt))
	}

	fwNames := map[string]struct{}{}
	for _, name := range FrameworkMetricNames() {
		fwNames[name] = struct{}{}
	}

	pendingNames := make([]string, 0, len(metrics))
	pendingMetrics := make([]interface{}, 0, len(metrics))
	batchNames := map[string]struct{}{}

	for i, m := range metrics {
		name, err := metricName(m)
		if err != nil {
			panic(fmt.Sprintf("apm: refuse to register db metric for DbType %s at index %d, errmsg: %s", dt, i, err))
		}
		if _, ok := fwNames[name]; ok {
			panic(fmt.Sprintf(
				"apm: refuse to register db metric %q for DbType %s: collides with framework metric", name, dt))
		}
		if _, ok := batchNames[name]; ok {
			panic(fmt.Sprintf(
				"apm: refuse to register duplicate db metric %q within same call for DbType %s", name, dt))
		}
		batchNames[name] = struct{}{}
		pendingNames = append(pendingNames, name)
		pendingMetrics = append(pendingMetrics, m)
	}

	dbMetricsMu.Lock()
	defer dbMetricsMu.Unlock()

	for _, name := range pendingNames {
		if _, ok := dbMetricsByName[name]; ok {
			panic(fmt.Sprintf(
				"apm: refuse to register db metric %q for DbType %s: already registered by a provider", name, dt))
		}
	}

	for i, name := range pendingNames {
		dbMetricsByName[name] = struct{}{}
		dbMetricsOrdered = append(dbMetricsOrdered, pendingMetrics[i])
	}
	dbMetricsDbTypes[dt] = struct{}{}
}

// DbMetrics returns provider-registered metrics in registration order.
func DbMetrics() []interface{} {
	dbMetricsMu.RLock()
	defer dbMetricsMu.RUnlock()
	out := make([]interface{}, len(dbMetricsOrdered))
	copy(out, dbMetricsOrdered)
	return out
}

// MetricRegisteredDbTypes returns DbTypes that registered their own metrics.
func MetricRegisteredDbTypes() []haprobe.DbType {
	dbMetricsMu.RLock()
	defer dbMetricsMu.RUnlock()
	out := make([]haprobe.DbType, 0, len(dbMetricsDbTypes))
	for dt := range dbMetricsDbTypes {
		out = append(out, dt)
	}
	sort.Slice(out, func(i, j int) bool {
		return string(out[i]) < string(out[j])
	})
	return out
}
