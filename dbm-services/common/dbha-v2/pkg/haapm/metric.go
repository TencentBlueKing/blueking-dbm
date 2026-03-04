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

// Metric holds the definition and the Prometheus collector for a metric.
// Collector is set by the Server when it registers the metric.
type Metric struct {
	Collector   prometheus.Collector
	Name        string
	Description string
	Type        string
	Labels      []string
	Buckets     []float64
	Objectives  map[float64]float64
}

// MetricGetter is implemented by all haapm metric types (HaCounter, HaGauge, HaHistogram, HaSummary).
// It is used by Server.Register and MustRegister to collect metrics for Prometheus.
type MetricGetter interface {
	ToMetric() *Metric
}

type MetricType string

func (m MetricType) String() string {
	return string(m)
}

const (
	MetricTypeGauge        MetricType = "gauge"
	MetricTypeGaugeVec     MetricType = "gauge_vec"
	MetricTypeCounter      MetricType = "counter"
	MetricTypeCounterVec   MetricType = "counter_vec"
	MetricTypeHistogram    MetricType = "histogram"
	MetricTypeHistogramVec MetricType = "histogram_vec"
	MetricTypeSummary      MetricType = "summary"
	MetricTypeSummaryVec   MetricType = "summary_vec"
)

var (
	AppStartupMetric *HaGauge
)

const (
	MetricLabelServiceID   = "service_id"
	MetricLabelServiceName = "service_name"
	MetricLabelServiceIP   = "service_ip"
	MetricLabelServicePort = "service_port"
	MetricLabelServiceNice = "nice"
)

func init() {
	AppStartupMetric = NewHaGauge("dbha_startup_time_sec",
		"The duration of how long the DBHA-V2 server has been running.",
		MetricLabelServiceID, MetricLabelServiceName)
}
