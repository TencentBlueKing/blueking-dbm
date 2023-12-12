/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package metric TODO
package metric

import (
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus"
)

var defaultMetricPath = "/metrics"
var defaultPingPath = "/ping"
var defaultBuckets = []float64{0, 0.05, 0.1, 0.2, 0.5, 1, 3, 5, 10, 20, 30, 60}

// Standard default metrics
//
//	counter, counter_vec, gauge, gauge_vec,
//	histogram, histogram_vec, summary, summary_vec
var reqCnt = &Metric{
	ID:          "reqCnt",
	Name:        "requests_total",
	Description: "How many HTTP requests processed, partitioned by status code and HTTP method.",
	Type:        "counter_vec",
	Labels:      []string{"code", "method", "handler", "host", "url"},
	Buckets:     defaultBuckets,
}

var reqDur = &Metric{
	ID:          "reqDur",
	Name:        "request_duration_seconds",
	Description: "The HTTP request latencies in seconds.",
	Type:        "histogram_vec",
	Labels:      []string{"code", "method", "url"},
	Buckets:     defaultBuckets,
}

var resSz = &Metric{
	ID:          "resSz",
	Name:        "response_size_bytes",
	Description: "The HTTP response sizes in bytes.",
	Type:        "summary",
}

var reqSz = &Metric{
	ID:          "reqSz",
	Name:        "request_size_bytes",
	Description: "The HTTP request sizes in bytes.",
	Type:        "summary",
}

var standardMetrics = []*Metric{
	reqCnt,
	reqDur,
	resSz,
	reqSz,
}

// Metrics is mapped for Metric object by Metric's ID
var Metrics = make(map[string]*Metric)

/*
RequestCounterURLLabelMappingFn is a function which can be supplied to the middleware to control
the cardinality of the request counter's "url" label, which might be required in some contexts.
For instance, if for a "/customer/:name" route you don't want to generate a time series for every
possible customer name, you could use this function:

	func(c *gin.Context) string {
		url := c.Request.URL.Path
		for _, p := range c.Params {
			if p.Key == "name" {
				url = strings.Replace(url, p.Value, ":name", 1)
				break
			}
		}
		return url
	}

which would map "/customer/alice" and "/customer/bob" to their template "/customer/:name".
*/
type RequestCounterURLLabelMappingFn func(c *gin.Context) string

// Metric is a definition for the name, description, type, ID, and
// prometheus.Collector type (i.e. CounterVec, Summary, etc) of each metric
type Metric struct {
	Collector   prometheus.Collector
	ID          string
	Name        string
	Description string
	Type        string
	Labels      []string
	Buckets     []float64
	Objectives  map[float64]float64
}

// NewMetric associates prometheus.Collector based on Metric.Type
func NewMetric(m *Metric, subsystem string) prometheus.Collector {
	var metric prometheus.Collector
	switch m.Type {
	case "counter_vec":
		metric = prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
			m.Labels,
		)
	case "counter":
		metric = prometheus.NewCounter(
			prometheus.CounterOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
		)
	case "gauge_vec":
		metric = prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
			m.Labels,
		)
	case "gauge":
		metric = prometheus.NewGauge(
			prometheus.GaugeOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
		)
	case "histogram_vec":
		metric = prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
				Buckets:   m.Buckets,
			},
			m.Labels,
		)
	case "histogram":
		metric = prometheus.NewHistogram(
			prometheus.HistogramOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
			},
		)
	case "summary_vec":
		metric = prometheus.NewSummaryVec(
			prometheus.SummaryOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
				// Objectives: m.Objectives,
			},
			m.Labels,
		)
	case "summary":
		metric = prometheus.NewSummary(
			prometheus.SummaryOpts{
				Subsystem: subsystem,
				Name:      m.Name,
				Help:      m.Description,
				// Objectives: m.Objectives,
			},
		)
	}
	return metric
}

// Id get metric by id
func Id(id string) *Metric {
	return Metrics[id]
}

// Add value to metric
func (m *Metric) Add(value float64, labels ...string) {
	switch m.Type {
	case "counter":
		m.Collector.(prometheus.Counter).Add(value)
	case "counter_vec":
		m.Collector.(*prometheus.CounterVec).WithLabelValues(labels...).Add(value)
	case "gauge":
		m.Collector.(prometheus.Gauge).Add(value)
	case "gauge_vec":
		m.Collector.(*prometheus.GaugeVec).WithLabelValues(labels...).Add(value)
	default:
		logger.Error("unsupported metric type: " + m.Type)
	}
}

// Inc increments the metric
func (m *Metric) Inc(labels ...string) {
	m.Add(1, labels...)
}

// Observe updates the metric
func (m *Metric) Observe(value float64, labels ...string) {
	switch m.Type {
	case "histogram":
		m.Collector.(prometheus.Histogram).Observe(value)
	case "histogram_vec":
		m.Collector.(*prometheus.HistogramVec).WithLabelValues(labels...).Observe(value)
	case "summary":
		m.Collector.(prometheus.Summary).Observe(value)
	case "summary_vec":
		m.Collector.(*prometheus.SummaryVec).WithLabelValues(labels...).Observe(value)
	default:
		logger.Error("unsupported metric type: " + m.Type)
	}
}
