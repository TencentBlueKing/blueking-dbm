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
	"dbm-services/common/go-pubpkg/apm/metric"

	"github.com/prometheus/client_golang/prometheus"
)

// A HaSummary captures individual observations from an event or sample stream and
// summarizes them in a manner similar to traditional summary statistics: 1. sum
// of observations, 2. observation count, 3. rank estimations.
//
// A typical use-case is the observation of request latencies. By default, a
// Summary provides the median, the 90th and the 99th percentile of the latency
// as rank estimations. However, the default behavior will change in the
// upcoming v1.0.0 of the library. There will be no rank estimations at all by
// default. For a sane transition, it is recommended to set the desired rank
// estimations explicitly.
//
// Note that the rank estimations cannot be aggregated in a meaningful way with
// the Prometheus query language (i.e. you cannot average or add them). If you
// need aggregatable quantiles (e.g. you want the 99th percentile latency of all
// queries served across all instances of a service), consider the Histogram
// metric type. See the Prometheus documentation for more details.
//
// To create HaSummary instances, use NewHaSummary.
type HaSummary struct {
	metric      *metric.Metric
	labelNames  []string
	labelValues map[string]string
}

func (m *HaSummary) ToMetric() *metric.Metric {
	return (*metric.Metric)(m.metric)
}

func (m *HaSummary) UpdateLabel(lvs map[string]string) *HaSummary {
	if len(m.labelNames) == 0 {
		panic("Update the gauge value with the new label values.")
	}

	for key, val := range lvs {
		m.labelValues[key] = val
	}

	return m
}

func (m *HaSummary) Observe(val float64) {
	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Summary).Observe(val)
		return
	}

	// Must keep the label value sequence the same as the label names.
	values := m.getLabelValues()

	if len(values) == len(m.labelNames) && len(m.labelValues) == len(m.labelNames) {
		m.metric.Collector.(*prometheus.SummaryVec).WithLabelValues(values...).Observe(val)
		return
	}

	// Reset the label values.
	m.resetLabelValues()
}

func (m *HaSummary) getLabelValues() []string {
	values := []string{}

	for _, name := range m.labelNames {
		if val, ok := m.labelValues[name]; ok {
			values = append(values, val)
		}
	}

	return values
}

func (m *HaSummary) resetLabelValues() {
	m.labelValues = map[string]string{}
	for _, name := range m.labelNames {
		m.labelValues[name] = "" // set default label value
	}
}

func NewHaSummary(name, help string, labelNames ...string) *HaSummary {
	summary := &HaSummary{}
	summary.metric = &metric.Metric{
		ID:          name,
		Name:        name,
		Description: help,
	}

	if len(labelNames) == 0 {
		summary.metric.Type = MetricTypeSummary.String()
		return summary
	}

	summary.metric.Type = MetricTypeSummaryVec.String()
	summary.labelNames = append(summary.labelNames, labelNames...)
	summary.metric.Labels = summary.labelNames

	return summary
}
