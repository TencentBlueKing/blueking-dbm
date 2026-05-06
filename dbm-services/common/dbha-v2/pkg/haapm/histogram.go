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
	"sync"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/prometheus/client_golang/prometheus"
)

// HaHistogram A HaHistogram counts individual observations from an event or sample stream in
// configurable static buckets (or in dynamic sparse buckets as part of the
// experimental Native Histograms, see below for more details). Similar to a
// Summary, it also provides a sum of observations and an observation count.
//
// The Observe method of a HaHistogram has a very low performance overhead in
// comparison with the Observe method of a Summary.
//
// To create HaHistogram instances, use NewHaHistogram.
type HaHistogram struct {
	Error error

	mu          sync.Mutex
	metric      *Metric
	labelNames  []string
	labelValues map[string]string
}

// ToMetric returns the metric.
func (m *HaHistogram) ToMetric() *Metric {
	return m.metric
}

// WithLabels returns a BoundHistogram with fixed labels. For static resources, create once
// and use the bound in business code so only Observe() is needed.
func (m *HaHistogram) WithLabels(labels map[string]string) *BoundHistogram {
	return &BoundHistogram{histogram: m, labels: copyLabels(labels)}
}

// UpdateLabel sets label values for the next Observe call.
//
// WARNING: This method is NOT atomic with the subsequent Observe call.
// In concurrent code, use ObserveWithLabels instead, which performs the full
// label-write + observe + reset atomically under a single lock.
func (m *HaHistogram) UpdateLabel(lvs map[string]string) *HaHistogram {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.Error != nil {
		return m
	}

	if len(m.labelNames) == 0 {
		m.Error = gerrors.New(gerrors.InvalidParameter, "invalid labels")
		return m
	}

	for key, val := range lvs {
		if _, ok := m.labelValues[key]; ok {
			m.labelValues[key] = val
			continue
		}

		m.Error = gerrors.Newf(gerrors.InvalidParameter, "label is mismatched: %s", key)
		return m
	}

	m.Error = nil
	return m
}

// Observe adds a single observation to the histogram.
func (m *HaHistogram) Observe(val float64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.Error != nil {
		return m.Error
	}

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Histogram).Observe(val)
		return m.Error
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.HistogramVec).With(m.labelValues).Observe(val)
	return m.Error
}

// ObserveWithLabels performs the full label-write + observe + reset atomically
// under a single lock. This is the goroutine-safe entry point for concurrent code.
func (m *HaHistogram) ObserveWithLabels(labels map[string]string, val float64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Histogram).Observe(val)
		return nil
	}

	// Apply labels directly
	for k, v := range labels {
		if _, ok := m.labelValues[k]; !ok {
			return gerrors.Newf(gerrors.InvalidParameter, "label is mismatched: %s", k)
		}
		m.labelValues[k] = v
	}

	if len(m.labelValues) != len(m.labelNames) {
		return gerrors.New(gerrors.InvalidParameter, "label is mismatched")
	}

	m.metric.Collector.(*prometheus.HistogramVec).With(m.labelValues).Observe(val)
	return nil
}

// reset resets the label values.
func (m *HaHistogram) reset() {
	m.labelValues = map[string]string{}
	for _, name := range m.labelNames {
		m.labelValues[name] = "" // set default label value
	}

	m.Error = nil
}

// NewHaHistogram creates a new HaHistogram.
func NewHaHistogram(name, help string, labelNames ...string) *HaHistogram {
	histogram := &HaHistogram{}
	histogram.metric = &Metric{
		Name:        name,
		Description: help,
	}

	if len(labelNames) == 0 {
		histogram.metric.Type = MetricTypeHistogram.String()
		return histogram
	}

	histogram.metric.Type = MetricTypeHistogramVec.String()
	histogram.labelNames = append(histogram.labelNames, labelNames...)
	histogram.metric.Labels = histogram.labelNames

	histogram.reset()
	return histogram
}

// NewHaHistogramWithBuckets creates a new HaHistogram with buckets.
func NewHaHistogramWithBuckets(name, help string, buckets []float64, labelNames ...string) *HaHistogram {
	histogram := &HaHistogram{}
	histogram.metric = &Metric{
		Name:        name,
		Description: help,
	}

	if len(buckets) != 0 {
		histogram.metric.Buckets = append(histogram.metric.Buckets, buckets...)
	}

	if len(labelNames) == 0 {
		histogram.metric.Type = MetricTypeHistogram.String()
		return histogram
	}

	histogram.metric.Type = MetricTypeHistogramVec.String()
	histogram.labelNames = append(histogram.labelNames, labelNames...)
	histogram.metric.Labels = histogram.labelNames

	histogram.reset()
	return histogram
}
