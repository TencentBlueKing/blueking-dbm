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
	"testing"

	"github.com/prometheus/client_golang/prometheus"
	dto "github.com/prometheus/client_model/go"
	"github.com/stretchr/testify/require"
)

func TestMaterializeZeroExportsZeroBeforeObservation(t *testing.T) {
	reg := prometheus.NewRegistry()
	counter := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "seed_counter_total",
		Help: "seed counter",
	}, []string{"topic"})
	hist := prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "seed_delay_ms",
		Help:    "seed delay",
		Buckets: []float64{1, 5},
	}, []string{"topic"})
	gauge := prometheus.NewGaugeVec(prometheus.GaugeOpts{
		Name: "seed_gauge",
		Help: "seed gauge",
	}, []string{"service_id"})
	require.NoError(t, reg.Register(counter))
	require.NoError(t, reg.Register(hist))
	require.NoError(t, reg.Register(gauge))

	materializeZero(counter, []string{"topic"})
	materializeZero(hist, []string{"topic"})
	materializeZero(gauge, []string{"service_id"})

	families, err := reg.Gather()
	require.NoError(t, err)
	require.Equal(t, 0.0, sampleCounter(t, families, "seed_counter_total", "topic", ""))
	require.Equal(t, uint64(0), sampleHistogramCount(t, families, "seed_delay_ms", "topic", ""))
	require.Equal(t, 0.0, sampleGauge(t, families, "seed_gauge", "service_id", ""))

	counter.With(prometheus.Labels{"topic": "probe"}).Inc()
	hist.With(prometheus.Labels{"topic": "probe"}).Observe(2)
	gauge.With(prometheus.Labels{"service_id": "svc"}).Set(10)

	families, err = reg.Gather()
	require.NoError(t, err)
	require.Equal(t, 0.0, sampleCounter(t, families, "seed_counter_total", "topic", ""))
	require.Equal(t, 1.0, sampleCounter(t, families, "seed_counter_total", "topic", "probe"))
	require.Equal(t, uint64(0), sampleHistogramCount(t, families, "seed_delay_ms", "topic", ""))
	require.Equal(t, uint64(1), sampleHistogramCount(t, families, "seed_delay_ms", "topic", "probe"))
	require.Equal(t, 0.0, sampleGauge(t, families, "seed_gauge", "service_id", ""))
	require.Equal(t, 10.0, sampleGauge(t, families, "seed_gauge", "service_id", "svc"))
}

func sampleCounter(t *testing.T, families []*dto.MetricFamily, name, label, value string) float64 {
	t.Helper()
	m := findSample(t, families, name, label, value)
	require.NotNil(t, m.Counter)
	return m.Counter.GetValue()
}

func sampleGauge(t *testing.T, families []*dto.MetricFamily, name, label, value string) float64 {
	t.Helper()
	m := findSample(t, families, name, label, value)
	require.NotNil(t, m.Gauge)
	return m.Gauge.GetValue()
}

func sampleHistogramCount(t *testing.T, families []*dto.MetricFamily, name, label, value string) uint64 {
	t.Helper()
	m := findSample(t, families, name, label, value)
	require.NotNil(t, m.Histogram)
	return m.Histogram.GetSampleCount()
}

func findSample(t *testing.T, families []*dto.MetricFamily, name, label, value string) *dto.Metric {
	t.Helper()
	for _, f := range families {
		if f.GetName() != name {
			continue
		}
		for _, m := range f.Metric {
			if labelValue(m, label) == value {
				return m
			}
		}
	}
	t.Fatalf("metric %s label %s=%q not found", name, label, value)
	return nil
}

func labelValue(m *dto.Metric, name string) string {
	for _, p := range m.Label {
		if p.GetName() == name {
			return p.GetValue()
		}
	}
	return ""
}
