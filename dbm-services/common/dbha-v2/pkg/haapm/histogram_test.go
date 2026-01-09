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

	"dbm-services/common/go-pubpkg/apm/metric"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func createTestHistogram(name, help string, labelNames ...string) *HaHistogram {
	histogram := NewHaHistogram(name, help, labelNames...)

	metricDef := histogram.ToMetric()
	histogram.metric.Collector = metric.NewMetric(metricDef, "dbha-v2-test")
	return histogram
}

func createTestHistogramWithBuckets(name, help string, buckets []float64, labelNames ...string) *HaHistogram {
	histogram := NewHaHistogramWithBuckets(name, help, buckets, labelNames...)

	metricDef := histogram.ToMetric()
	histogram.metric.Collector = metric.NewMetric(metricDef, "dbha-v2-receiver-test")
	return histogram
}

func TestNewHaHistogram(t *testing.T) {
	tests := []struct {
		name       string
		metricName string
		help       string
		labelNames []string
		wantType   string
	}{
		{
			name:       "histogram without labels",
			metricName: "test_histogram",
			help:       "test histogram help",
			labelNames: nil,
			wantType:   MetricTypeHistogram.String(),
		},
		{
			name:       "histogram with single label",
			metricName: "test_histogram_vec",
			help:       "test histogram vec help",
			labelNames: []string{"label1"},
			wantType:   MetricTypeHistogramVec.String(),
		},
		{
			name:       "histogram with multiple labels",
			metricName: "test_histogram_multi",
			help:       "test histogram multi help",
			labelNames: []string{"label1", "label2", "label3"},
			wantType:   MetricTypeHistogramVec.String(),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			histogram := NewHaHistogram(tt.metricName, tt.help, tt.labelNames...)

			require.NotNil(t, histogram)
			require.NotNil(t, histogram.metric)
			assert.Equal(t, tt.metricName, histogram.metric.Name)
			assert.Equal(t, tt.help, histogram.metric.Description)
			assert.Equal(t, tt.wantType, histogram.metric.Type)
			assert.Equal(t, tt.labelNames, histogram.labelNames)

			if len(tt.labelNames) > 0 {
				require.NotNil(t, histogram.labelValues)
				assert.Equal(t, len(tt.labelNames), len(histogram.labelValues))
				for _, name := range tt.labelNames {
					assert.Equal(t, "", histogram.labelValues[name])
				}
			}
		})
	}
}

func TestNewHaHistogramWithBuckets(t *testing.T) {
	tests := []struct {
		name       string
		metricName string
		help       string
		buckets    []float64
		labelNames []string
		wantType   string
	}{
		{
			name:       "histogram with custom buckets",
			metricName: "test_histogram_buckets",
			help:       "test histogram with buckets",
			buckets:    []float64{0.1, 0.5, 1.0, 5.0, 10.0},
			labelNames: nil,
			wantType:   MetricTypeHistogram.String(),
		},
		{
			name:       "histogram with custom buckets and labels",
			metricName: "test_histogram_buckets_vec",
			help:       "test histogram with buckets and labels",
			buckets:    []float64{1, 10, 100, 1000},
			labelNames: []string{"method", "status"},
			wantType:   MetricTypeHistogramVec.String(),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			histogram := NewHaHistogramWithBuckets(tt.metricName, tt.help, tt.buckets, tt.labelNames...)

			require.NotNil(t, histogram)
			require.NotNil(t, histogram.metric)
			assert.Equal(t, tt.metricName, histogram.metric.Name)
			assert.Equal(t, tt.help, histogram.metric.Description)
			assert.Equal(t, tt.wantType, histogram.metric.Type)
			assert.Equal(t, tt.labelNames, histogram.labelNames)

			if len(tt.labelNames) > 0 {
				require.NotNil(t, histogram.labelValues)
				assert.Equal(t, len(tt.labelNames), len(histogram.labelValues))
			}
		})
	}
}

func TestHaHistogram_Observe(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaHistogram
		value     float64
		wantError bool
	}{
		{
			name: "observe without labels",
			setup: func() *HaHistogram {
				return createTestHistogram("test_histogram_observe", "test help")
			},
			value:     42.5,
			wantError: false,
		},
		{
			name: "observe with valid labels",
			setup: func() *HaHistogram {
				histogram := createTestHistogram("test_histogram_observe_vec", "test help", "label1")
				histogram.UpdateLabel(map[string]string{"label1": "value1"})
				return histogram
			},
			value:     100.0,
			wantError: false,
		},
		{
			name: "observe with missing labels",
			setup: func() *HaHistogram {
				histogram := createTestHistogram("test_histogram_observe_missing", "test help", "label1")
				histogram.UpdateLabel(map[string]string{"label1": "value1"})
				histogram.UpdateLabel(map[string]string{"label2": "value2"})
				return histogram
			},
			value:     50.0,
			wantError: true,
		},
		{
			name: "observe zero value",
			setup: func() *HaHistogram {
				return createTestHistogram("test_histogram_observe_zero", "test help")
			},
			value:     0.0,
			wantError: false,
		},
		{
			name: "observe negative value",
			setup: func() *HaHistogram {
				return createTestHistogram("test_histogram_observe_negative", "test help")
			},
			value:     -10.5,
			wantError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			histogram := tt.setup()
			err := histogram.Observe(tt.value)

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaHistogram_ObserveWithBuckets(t *testing.T) {
	t.Run("observe values in different buckets", func(t *testing.T) {
		buckets := []float64{1.0, 5.0, 10.0, 50.0, 100.0}
		histogram := createTestHistogramWithBuckets("test_histogram_buckets_observe", "test help", buckets)

		values := []float64{0.5, 3.0, 7.0, 25.0, 75.0, 150.0}
		for _, val := range values {
			err := histogram.Observe(val)
			assert.NoError(t, err)
		}
	})

	t.Run("observe with custom buckets and labels", func(t *testing.T) {
		buckets := []float64{10, 50, 100, 500, 1000}
		histogram := createTestHistogramWithBuckets(
			"test_histogram_buckets_labels",
			"test help",
			buckets,
			"method",
		)

		histogram.UpdateLabel(map[string]string{"method": "GET"})
		err := histogram.Observe(250.0)
		assert.NoError(t, err)
	})
}

func TestHaHistogram_UpdateLabel(t *testing.T) {
	tests := []struct {
		name       string
		setup      func() *HaHistogram
		labels     map[string]string
		wantError  bool
		checkLabel func(*testing.T, *HaHistogram)
	}{
		{
			name: "update valid label",
			setup: func() *HaHistogram {
				return NewHaHistogram("test_histogram", "test help", "label1")
			},
			labels:    map[string]string{"label1": "value1"},
			wantError: false,
			checkLabel: func(t *testing.T, h *HaHistogram) {
				assert.Equal(t, "value1", h.labelValues["label1"])
			},
		},
		{
			name: "update multiple labels",
			setup: func() *HaHistogram {
				return NewHaHistogram("test_histogram", "test help", "label1", "label2")
			},
			labels:    map[string]string{"label1": "value1", "label2": "value2"},
			wantError: false,
			checkLabel: func(t *testing.T, h *HaHistogram) {
				assert.Equal(t, "value1", h.labelValues["label1"])
				assert.Equal(t, "value2", h.labelValues["label2"])
			},
		},
		{
			name: "update with invalid label name",
			setup: func() *HaHistogram {
				return NewHaHistogram("test_histogram", "test help", "label1")
			},
			labels:    map[string]string{"invalid_label": "value1"},
			wantError: true,
		},
		{
			name: "update histogram without labels",
			setup: func() *HaHistogram {
				return NewHaHistogram("test_histogram", "test help")
			},
			labels:    map[string]string{"label1": "value1"},
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			histogram := tt.setup()
			result := histogram.UpdateLabel(tt.labels)

			if tt.wantError {
				assert.Error(t, result.Error)
			} else {
				assert.NoError(t, result.Error)
				if tt.checkLabel != nil {
					tt.checkLabel(t, result)
				}
			}
		})
	}
}

func TestHaHistogram_Reset(t *testing.T) {
	t.Run("reset after Observe clears label values", func(t *testing.T) {
		histogram := createTestHistogram("test_histogram_reset1", "test help", "label1", "label2")

		histogram.UpdateLabel(map[string]string{
			"label1": "value1",
			"label2": "value2",
		})

		assert.Equal(t, "value1", histogram.labelValues["label1"])
		assert.Equal(t, "value2", histogram.labelValues["label2"])

		err := histogram.Observe(42.5)
		require.NoError(t, err)

		assert.Equal(t, "", histogram.labelValues["label1"])
		assert.Equal(t, "", histogram.labelValues["label2"])
		assert.Nil(t, histogram.Error)
	})

	t.Run("reset clears error state", func(t *testing.T) {
		histogram := createTestHistogram("test_histogram_reset2", "test help", "label1")

		histogram.UpdateLabel(map[string]string{"invalid": "value"})
		assert.NotNil(t, histogram.Error)

		histogram.reset()

		assert.Nil(t, histogram.Error)
		assert.Equal(t, "", histogram.labelValues["label1"])
	})

	t.Run("multiple observations with reset", func(t *testing.T) {
		histogram := createTestHistogram("test_histogram_reset3", "test help", "endpoint")

		histogram.UpdateLabel(map[string]string{"endpoint": "/api/v1"})
		err := histogram.Observe(10.5)
		require.NoError(t, err)
		assert.Equal(t, "", histogram.labelValues["endpoint"])

		histogram.UpdateLabel(map[string]string{"endpoint": "/api/v2"})
		err = histogram.Observe(25.3)
		require.NoError(t, err)
		assert.Equal(t, "", histogram.labelValues["endpoint"])

		histogram.UpdateLabel(map[string]string{"endpoint": "/api/v3"})
		err = histogram.Observe(50.0)
		require.NoError(t, err)
		assert.Equal(t, "", histogram.labelValues["endpoint"])
	})
}
