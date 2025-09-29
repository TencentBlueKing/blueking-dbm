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

	metric      *metric.Metric
	labelNames  []string
	labelValues map[string]string
}

func (m *HaGauge) ToMetric() *metric.Metric {
	return (*metric.Metric)(m.metric)
}

func (m *HaGauge) UpdateLabel(lvs map[string]string) *HaGauge {
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

func (m *HaGauge) Set(val float64) error {
	defer m.reset()

	if m.Error != nil {
		return m.Error
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Set(val)
		return m.Error
	}

	if len(m.labelValues) != len(m.labelValues) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Set(val)
	return m.Error
}

func (m *HaGauge) Inc() error {
	defer m.reset()

	if m.Error != nil {
		return m.Error
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Inc()
		return nil
	}

	if len(m.labelValues) != len(m.labelValues) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Inc()
	return m.Error
}

func (m *HaGauge) Dec() error {
	defer m.reset()

	if m.Error != nil {
		return m.Error
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Dec()
		return m.Error
	}

	if len(m.labelValues) != len(m.labelValues) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Dec()
	return m.Error
}

func (m *HaGauge) Add(val float64) error {
	defer m.reset()

	if m.Error != nil {
		return m.Error
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Add(val)
		return m.Error
	}

	if len(m.labelValues) != len(m.labelValues) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Add(val)
	return m.Error
}

func (m *HaGauge) Sub(val float64) error {
	defer m.reset()

	if m.Error != nil {
		return m.Error
	}

	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Gauge).Sub(val)
		return m.Error
	}

	if len(m.labelValues) != len(m.labelValues) {
		m.Error = gerrors.New(gerrors.InvalidParameter, "label is mismatched")
		return m.Error
	}

	m.metric.Collector.(*prometheus.GaugeVec).With(m.labelValues).Sub(val)
	return m.Error
}

func (m *HaGauge) reset() {
	m.Error = nil
}

func NewHaGauge(name, help string, labelNames ...string) *HaGauge {
	gauge := &HaGauge{}

	gauge.metric = &metric.Metric{
		ID:          name,
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
	for _, name := range gauge.labelNames {
		gauge.labelValues[name] = "" // set default label value
	}

	gauge.reset()
	return gauge
}
