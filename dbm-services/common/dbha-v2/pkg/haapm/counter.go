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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/go-pubpkg/apm/metric"

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

	metric      *metric.Metric
	labelNames  []string
	labelValues map[string]string
}

func (m *HaCounter) ToMetric() *metric.Metric {
	return (*metric.Metric)(m.metric)
}

func (m *HaCounter) UpdateLabel(lvs map[string]string) *HaCounter {
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

func (m *HaCounter) Inc() error {
	defer m.reset()

	if m.Error != nil {
		return m.Error
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Counter).Inc()
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.CounterVec).With(m.labelValues).Inc()
	return m.Error
}

func (m *HaCounter) Add(val float64) error {
	defer m.reset()

	if m.Error != nil {
		return m.Error
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Counter).Add(val)
		return nil
	}

	if len(m.labelValues) != len(m.labelNames) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.CounterVec).With(m.labelValues).Add(val)
	return m.Error
}

func (m *HaCounter) reset() {
	m.labelValues = map[string]string{}
	for _, name := range m.labelNames {
		m.labelValues[name] = "" // set default label value
	}

	m.Error = nil
}

func NewHaCounter(name, help string, labelNames ...string) *HaCounter {
	counter := &HaCounter{}
	counter.metric = &metric.Metric{
		ID:          name,
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
