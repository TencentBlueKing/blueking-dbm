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

// HaCounter is a Metric that represents a single numerical value that only ever
// goes up. That implies that it cannot be used to count items whose number can
// also go down, e.g. the number of currently running goroutines. Those
// "counters" are represented by Gauges.
//
// A Counter is typically used to count requests served, tasks completed, errors
// occurred, etc.
//
// To create HaCounter instances, use NewHaCounter.
type HaCounter struct {
	Error error

	mu          sync.Mutex
	metric      *Metric
	labelNames  []string
	labelValues map[string]string
}

// ToMetric returns the Metric.
func (m *HaCounter) ToMetric() *Metric {
	return m.metric
}

// WithLabels returns a BoundCounter with fixed labels. For static resources, create once
// and use the bound in business code so only Inc() or Add() is needed.
func (m *HaCounter) WithLabels(labels map[string]string) *BoundCounter {
	return &BoundCounter{counter: m, labels: copyLabels(labels)}
}

// UpdateLabel sets label values for the next Inc/Add call.
//
// WARNING: This method is NOT atomic with the subsequent Inc/Add call.
// In concurrent code, use IncWithLabels or AddWithLabels instead, which perform
// the full label-write + operation + reset atomically under a single lock.
func (m *HaCounter) UpdateLabel(lvs map[string]string) *HaCounter {
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

// Inc increments the counter by 1.
func (m *HaCounter) Inc() error {
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
		m.metric.Collector.(prometheus.Counter).Inc()
		return m.Error
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.CounterVec).With(m.labelValues).Inc()
	return m.Error
}

// Add adds the given value to the counter.
func (m *HaCounter) Add(val float64) error {
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
		m.metric.Collector.(prometheus.Counter).Add(val)
		return m.Error
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.CounterVec).With(m.labelValues).Add(val)
	return m.Error
}

// IncWithLabels performs the full label-write + inc + reset atomically
// under a single lock. This is the goroutine-safe entry point for concurrent code.
func (m *HaCounter) IncWithLabels(labels map[string]string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Counter).Inc()
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

	m.metric.Collector.(*prometheus.CounterVec).With(m.labelValues).Inc()
	return nil
}

// AddWithLabels performs the full label-write + add + reset atomically
// under a single lock. This is the goroutine-safe entry point for concurrent code.
func (m *HaCounter) AddWithLabels(labels map[string]string, val float64) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	defer m.reset()

	if m.metric.Collector == nil {
		return nil
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Counter).Add(val)
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

	m.metric.Collector.(*prometheus.CounterVec).With(m.labelValues).Add(val)
	return nil
}

func (m *HaCounter) reset() {
	m.labelValues = map[string]string{}
	for _, name := range m.labelNames {
		m.labelValues[name] = "" // set default label value
	}

	m.Error = nil
}

// NewHaCounter creates a new HaCounter.
func NewHaCounter(name, help string, labelNames ...string) *HaCounter {
	counter := &HaCounter{}
	counter.metric = &Metric{
		Name:        name,
		Description: help,
	}

	if len(labelNames) == 0 {
		counter.metric.Type = MetricTypeCounter.String()
		return counter
	}

	counter.metric.Type = MetricTypeCounterVec.String()
	counter.labelNames = append(counter.labelNames, labelNames...)
	counter.metric.Labels = counter.labelNames

	counter.reset()
	return counter
}
