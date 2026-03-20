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

// Bound types hold fixed labels so business code can call Inc/Observe/Set
// without repeating UpdateLabel(map[...]) every time. Create once with
// WithLabels, then use the bound handle everywhere.

func copyLabels(labels map[string]string) map[string]string {
	if labels == nil || len(labels) == 0 {
		return nil
	}
	cp := make(map[string]string, len(labels))
	for k, v := range labels {
		cp[k] = v
	}
	return cp
}

// BoundCounter is a counter with fixed labels. Create via HaCounter.WithLabels;
// then use Inc() or Add() in business code without passing labels again.
type BoundCounter struct {
	counter *HaCounter
	labels  map[string]string
}

// Inc increments the counter by 1.
func (b *BoundCounter) Inc() error {
	if b.labels == nil {
		return b.counter.Inc()
	}
	return b.counter.UpdateLabel(b.labels).Inc()
}

// Add adds the given value to the counter.
func (b *BoundCounter) Add(delta float64) error {
	if b.labels == nil {
		return b.counter.Add(delta)
	}
	return b.counter.UpdateLabel(b.labels).Add(delta)
}

// BoundGauge is a gauge with fixed labels. Create via HaGauge.WithLabels.
type BoundGauge struct {
	gauge  *HaGauge
	labels map[string]string
}

// Set sets the gauge value.
func (b *BoundGauge) Set(val float64) error {
	if b.labels == nil {
		return b.gauge.Set(val)
	}
	return b.gauge.UpdateLabel(b.labels).Set(val)
}

// Inc increments the gauge by 1.
func (b *BoundGauge) Inc() error {
	if b.labels == nil {
		return b.gauge.Inc()
	}
	return b.gauge.UpdateLabel(b.labels).Inc()
}

// Dec decrements the gauge by 1.
func (b *BoundGauge) Dec() error {
	if b.labels == nil {
		return b.gauge.Dec()
	}
	return b.gauge.UpdateLabel(b.labels).Dec()
}

// Add adds the given value to the gauge.
func (b *BoundGauge) Add(val float64) error {
	if b.labels == nil {
		return b.gauge.Add(val)
	}
	return b.gauge.UpdateLabel(b.labels).Add(val)
}

// Sub subtracts the given value from the gauge.
func (b *BoundGauge) Sub(val float64) error {
	if b.labels == nil {
		return b.gauge.Sub(val)
	}
	return b.gauge.UpdateLabel(b.labels).Sub(val)
}

// BoundHistogram is a histogram with fixed labels. Create via HaHistogram.WithLabels.
type BoundHistogram struct {
	histogram *HaHistogram
	labels    map[string]string
}

// Observe adds a single observation to the histogram.
func (b *BoundHistogram) Observe(val float64) error {
	if b.labels == nil {
		return b.histogram.Observe(val)
	}
	return b.histogram.UpdateLabel(b.labels).Observe(val)
}

// BoundSummary is a summary with fixed labels. Create via HaSummary.WithLabels.
type BoundSummary struct {
	summary *HaSummary
	labels  map[string]string
}

// Observe adds a single observation to the summary.
func (b *BoundSummary) Observe(val float64) error {
	if b.labels == nil {
		return b.summary.Observe(val)
	}
	return b.summary.UpdateLabel(b.labels).Observe(val)
}
