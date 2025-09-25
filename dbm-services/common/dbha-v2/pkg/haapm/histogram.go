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

// A HaHistogram counts individual observations from an event or sample stream in
// configurable static buckets (or in dynamic sparse buckets as part of the
// experimental Native Histograms, see below for more details). Similar to a
// Summary, it also provides a sum of observations and an observation count.
//
// The Observe method of a HaHistogram has a very low performance overhead in
// comparison with the Observe method of a Summary.
//
// To create HaHistogram instances, use NewHaHistogram.
type HaHistogram struct {
	metric      *metric.Metric
	labelNames  []string
	labelValues map[string]string
}

func (m *HaHistogram) ToMetric() *metric.Metric {
	return (*metric.Metric)(m.metric)
}

func (m *HaHistogram) UpdateLabel(lvs map[string]string) *HaHistogram {
	if len(m.labelNames) == 0 {
		panic("Update the gauge value with the new label values.")
	}

	for key, val := range lvs {
		m.labelValues[key] = val
	}

	return m
}

func (m *HaHistogram) Observe(val float64) {
	if len(m.labelNames) == 0 {
		m.metric.Collector.(prometheus.Histogram).Observe(val)
		return
	}

	// Must keep the label value sequence the same as the label names.
	values := m.getLabelValues()

	if len(values) == len(m.labelNames) && len(m.labelValues) == len(m.labelNames) {
		m.metric.Collector.(*prometheus.HistogramVec).WithLabelValues(values...).Observe(val)
		return
	}

	// Reset the label values.
	m.resetLabelValues()
}

func (m *HaHistogram) getLabelValues() []string {
	values := []string{}

	for _, name := range m.labelNames {
		if val, ok := m.labelValues[name]; ok {
			values = append(values, val)
		}
	}

	return values
}

func (m *HaHistogram) resetLabelValues() {
	m.labelValues = map[string]string{}
	for _, name := range m.labelNames {
		m.labelValues[name] = "" // set default label value
	}
}

func NewHaHistogram(name, help string, labelNames ...string) *HaHistogram {
	histogram := &HaHistogram{}
	histogram.metric = &metric.Metric{
		ID:          name,
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

	return histogram
}

func NewHaHistogramWithBuckets(name, help string, buckets []float64, labelNames ...string) *HaHistogram {
	histogram := &HaHistogram{}
	histogram.metric = &metric.Metric{
		ID:          name,
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

	return histogram
}
