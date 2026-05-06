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

// HaGauge is a Metric that represents a single numerical value that can
// arbitrarily go up and down.
//
// A HaGauge is typically used for measured values like temperatures or current
// memory usage, but also "counts" that can go up and down, like the number of
// running goroutines.
//
// To create HaGauge instances, use NewHaGauge.
type HaGauge struct {
	Error error

	mu          sync.Mutex
	metric      *Metric
	labelNames  []string
	labelValues map[string]string
}

// ToMetric returns the Metric.
func (m *HaGauge) ToMetric() *Metric {
	return m.metric
}

// WithLabels returns a BoundGauge with fixed labels. For static resources, create once
// and use the bound in business code so only Set/Inc/Dec/Add/Sub is needed.
func (m *HaGauge) WithLabels(labels map[string]string) *BoundGauge {
	return &BoundGauge{gauge: m, labels: copyLabels(labels)}
}

// UpdateLabel sets label values for the next Set/Inc/Dec/Add/Sub call.
//
// WARNING: This method is NOT atomic with the subsequent operation call.
// In concurrent code, use SetWithLabels/IncWithLabels/AddWithLabels etc. instead,
// which perform the full label-write + operation + reset atomically under a single lock.
func (m *HaGauge) UpdateLabel(lvs map[string]string) *HaGauge {
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

// Set sets the HaGauge to an arbitrary value.
func (m *HaGauge) Set(val float64) error {
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
		m.metric.Collector.(prometheus.Gauge).Set(val)
		return m.Error
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Set(val)
	return m.Error
}

// Inc increments the HaGauge by 1.
func (m *HaGauge) Inc() error {
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
		m.metric.Collector.(prometheus.Gauge).Inc()
		return m.Error
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Inc()
	return m.Error
}

// Dec decrements the HaGauge by 1.
func (m *HaGauge) Dec() error {
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
		m.metric.Collector.(prometheus.Gauge).Dec()
		return m.Error
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Dec()
	return m.Error
}

// Add adds the given value to the HaGauge.
func (m *HaGauge) Add(val float64) error {
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
		m.metric.Collector.(prometheus.Gauge).Add(val)
		return m.Error
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Add(val)
	return m.Error
}

// Sub subtracts the given value from the HaGauge.
func (m *HaGauge) Sub(val float64) error {
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
		m.metric.Collector.(prometheus.Gauge).Sub(val)
		return m.Error
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Sub(val)
	return m.Error
}

// SetWithLabels performs the full label-write + set + reset atomically
// under a single lock. This is the goroutine-safe entry point for concurrent code.
func (m *HaGauge) SetWithLabels(labels map[string]string, val float64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Set(val)
		return nil
	}

	for k, v := range labels {
		if _, ok := m.labelValues[k]; !ok {
			return gerrors.Newf(gerrors.InvalidParameter, "label is mismatched: %s", k)
		}
		m.labelValues[k] = v
	}

	if len(m.labelValues) != len(m.labelNames) {
		return gerrors.New(gerrors.InvalidParameter, "label is mismatched")
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Set(val)
	return nil
}

// IncWithLabels performs the full label-write + inc + reset atomically
// under a single lock. This is the goroutine-safe entry point for concurrent code.
func (m *HaGauge) IncWithLabels(labels map[string]string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Inc()
		return nil
	}

	for k, v := range labels {
		if _, ok := m.labelValues[k]; !ok {
			return gerrors.Newf(gerrors.InvalidParameter, "label is mismatched: %s", k)
		}
		m.labelValues[k] = v
	}

	if len(m.labelValues) != len(m.labelNames) {
		return gerrors.New(gerrors.InvalidParameter, "label is mismatched")
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Inc()
	return nil
}

// AddWithLabels performs the full label-write + add + reset atomically
// under a single lock. This is the goroutine-safe entry point for concurrent code.
func (m *HaGauge) AddWithLabels(labels map[string]string, val float64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Add(val)
		return nil
	}

	for k, v := range labels {
		if _, ok := m.labelValues[k]; !ok {
			return gerrors.Newf(gerrors.InvalidParameter, "label is mismatched: %s", k)
		}
		m.labelValues[k] = v
	}

	if len(m.labelValues) != len(m.labelNames) {
		return gerrors.New(gerrors.InvalidParameter, "label is mismatched")
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Add(val)
	return nil
}

// SubWithLabels performs the full label-write + sub + reset atomically
// under a single lock. This is the goroutine-safe entry point for concurrent code.
func (m *HaGauge) SubWithLabels(labels map[string]string, val float64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Sub(val)
		return nil
	}

	for k, v := range labels {
		if _, ok := m.labelValues[k]; !ok {
			return gerrors.Newf(gerrors.InvalidParameter, "label is mismatched: %s", k)
		}
		m.labelValues[k] = v
	}

	if len(m.labelValues) != len(m.labelNames) {
		return gerrors.New(gerrors.InvalidParameter, "label is mismatched")
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Sub(val)
	return nil
}

// DecWithLabels performs the full label-write + dec + reset atomically
// under a single lock. This is the goroutine-safe entry point for concurrent code.
func (m *HaGauge) DecWithLabels(labels map[string]string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Dec()
		return nil
	}

	for k, v := range labels {
		if _, ok := m.labelValues[k]; !ok {
			return gerrors.Newf(gerrors.InvalidParameter, "label is mismatched: %s", k)
		}
		m.labelValues[k] = v
	}

	if len(m.labelValues) != len(m.labelNames) {
		return gerrors.New(gerrors.InvalidParameter, "label is mismatched")
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Dec()
	return nil
}

func (m *HaGauge) reset() {
	m.labelValues = map[string]string{}
	for _, name := range m.labelNames {
		m.labelValues[name] = "" // set default label value
	}

	m.Error = nil
}

// Clear removes all metrics with label values from the underlying GaugeVec.
// Typical usage: periodic snapshot metrics that need the previous window's
// series to be discarded before the next window is written.
//
// NOTE: For a gauge without label names, this is a no-op.
func (m *HaGauge) Clear() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.metric == nil || m.metric.Collector == nil {
		return
	}
	if vec, ok := m.metric.Collector.(*prometheus.GaugeVec); ok {
		vec.Reset() // prometheus sdk native Reset: drops all children
	}
}

// NewHaGauge creates a new HaGauge.
func NewHaGauge(name, help string, labelNames ...string) *HaGauge {
	gauge := &HaGauge{}

	gauge.metric = &Metric{
		Name:        name,
		Description: help,
	}

	if len(labelNames) == 0 {
		gauge.metric.Type = MetricTypeGauge.String()
		return gauge
	}

	gauge.metric.Type = MetricTypeGaugeVec.String()
	gauge.labelNames = append(gauge.labelNames, labelNames...)
	gauge.metric.Labels = gauge.labelNames
	gauge.labelValues = map[string]string{}
	for _, n := range gauge.labelNames {
		gauge.labelValues[n] = "" // set default label value
	}

	gauge.reset()
	return gauge
}
