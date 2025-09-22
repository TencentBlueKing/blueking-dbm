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

import "dbm-services/common/go-pubpkg/apm/metric"

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
	metric *metric.Metric
}

func (m *HaCounter) ToMetric() *metric.Metric {
	return (*metric.Metric)(m.metric)
}

func (m *HaCounter) Inc() {
	m.metric.Inc()
}

func (m *HaCounter) Add(val float64) {
	m.metric.Add(val)
}

func NewHaCounter(name, help string, labels ...string) *HaCounter {
	counter := &HaCounter{}
	counter.metric = &metric.Metric{
		ID:          name,
		Name:        name,
		Description: help,
	}

	if len(labels) == 0 {
		counter.metric.Type = MetricTypeCounter.String()
	} else {
		counter.metric.Type = MetricTypeCounterVec.String()
		counter.metric.Labels = append(counter.metric.Labels, labels...)
	}

	return counter
}
