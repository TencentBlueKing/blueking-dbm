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
	"github.com/prometheus/client_golang/prometheus"
)

// newCollector creates a Prometheus collector from a Metric definition.
func newCollector(m *Metric, subsystem string) prometheus.Collector {
	switch m.Type {
	case MetricTypeCounterVec.String():
		return prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
			m.Labels,
		)
	case MetricTypeCounter.String():
		return prometheus.NewCounter(
			prometheus.CounterOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
		)
	case MetricTypeGaugeVec.String():
		return prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
			m.Labels,
		)
	case MetricTypeGauge.String():
		return prometheus.NewGauge(
			prometheus.GaugeOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
		)
	case MetricTypeHistogramVec.String():
		return prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
				Buckets:   m.Buckets,
			},
			m.Labels,
		)
	case MetricTypeHistogram.String():
		return prometheus.NewHistogram(
			prometheus.HistogramOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
				Buckets:   m.Buckets,
			},
		)
	case MetricTypeSummaryVec.String():
		return prometheus.NewSummaryVec(
			prometheus.SummaryOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
			m.Labels,
		)
	case MetricTypeSummary.String():
		return prometheus.NewSummary(
			prometheus.SummaryOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
		)
	default:
		return nil
	}
}

// materializeZero creates one zero-valued series for a labeled vector so the
// metric appears in scrapes before any real observation. Unlabeled collectors
// already export zero and are skipped. Histogram and summary series are created
// with With only, so their sample count stays zero.
func materializeZero(col prometheus.Collector, names []string) {
	if len(names) == 0 {
		return
	}
	labels := prometheus.Labels{}
	for _, n := range names {
		labels[n] = ""
	}
	switch c := col.(type) {
	case *prometheus.CounterVec:
		c.With(labels)
	case *prometheus.GaugeVec:
		c.With(labels).Set(0)
	case *prometheus.HistogramVec:
		c.With(labels)
	case *prometheus.SummaryVec:
		c.With(labels)
	}
}
