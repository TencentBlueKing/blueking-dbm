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

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func createTestCounter(name, help string, labelNames ...string) *HaCounter {
	counter := NewHaCounter(name, help, labelNames...)
	counter.metric.Collector = newCollector(counter.ToMetric(), "dbha-v2-test")
	return counter
}

func TestNewHaCounter(t *testing.T) {
	tests := []struct {
		name       string
		metricName string
		help       string
		labelNames []string
		wantType   string
	}{
		{
			name:       "counter without labels",
			metricName: "test_counter",
			help:       "test counter help",
			labelNames: nil,
			wantType:   MetricTypeCounter.String(),
		},
		{
			name:       "counter with single label",
			metricName: "test_counter_vec",
			help:       "test counter vec help",
			labelNames: []string{"label1"},
			wantType:   MetricTypeCounterVec.String(),
		},
		{
			name:       "counter with multiple labels",
			metricName: "test_counter_multi",
			help:       "test counter multi help",
			labelNames: []string{"label1", "label2", "label3"},
			wantType:   MetricTypeCounterVec.String(),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			counter := NewHaCounter(tt.metricName, tt.help, tt.labelNames...)

			require.NotNil(t, counter)
			require.NotNil(t, counter.metric)
			assert.Equal(t, tt.metricName, counter.metric.Name)
			assert.Equal(t, tt.help, counter.metric.Description)
			assert.Equal(t, tt.wantType, counter.metric.Type)
			assert.Equal(t, tt.labelNames, counter.labelNames)

			if len(tt.labelNames) > 0 {
				require.NotNil(t, counter.labelValues)
				assert.Equal(t, len(tt.labelNames), len(counter.labelValues))
				for _, name := range tt.labelNames {
					assert.Equal(t, "", counter.labelValues[name])
				}
			}
		})
	}
}

func TestHaCounter_Inc(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaCounter
		wantError bool
	}{
		{
			name: "inc without labels",
			setup: func() *HaCounter {
				return createTestCounter("test_counter_inc", "test help")
			},
			wantError: false,
		},
		{
			name: "inc with valid labels",
			setup: func() *HaCounter {
				counter := createTestCounter("test_counter_inc_vec", "test help", "label1")
				counter.UpdateLabel(map[string]string{"label1": "value1"})
				return counter
			},
			wantError: false,
		},
		{
			name: "inc with missing labels",
			setup: func() *HaCounter {
				counter := createTestCounter("test_counter_inc_missing", "test help", "label1")
				counter.UpdateLabel(map[string]string{"label1": "value1"})
				counter.UpdateLabel(map[string]string{"label2": "value2"})
				counter.UpdateLabel(map[string]string{"label3": "value3"})
				return counter

			},
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			counter := tt.setup()
			err := counter.Inc()

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaCounter_Add(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaCounter
		value     float64
		wantError bool
	}{
		{
			name: "add without labels",
			setup: func() *HaCounter {
				return createTestCounter("test_counter_add", "test help")
			},
			value:     10.5,
			wantError: false,
		},
		{
			name: "add with valid labels",
			setup: func() *HaCounter {
				counter := createTestCounter("test_counter_add_vec", "test help", "label1")
				counter.UpdateLabel(map[string]string{"label1": "value1"})
				return counter
			},
			value:     20.3,
			wantError: false,
		},
		{
			name: "add with missing labels",
			setup: func() *HaCounter {
				counter := createTestCounter("test_counter_add_missing", "test help", "label1")
				counter.UpdateLabel(map[string]string{"label1": "value1"})
				counter.UpdateLabel(map[string]string{"label2": "value2"})
				counter.UpdateLabel(map[string]string{"label3": "value3"})
				return counter

			},
			value:     5.0,
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			counter := tt.setup()
			err := counter.Add(tt.value)

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaCounter_UpdateLabel(t *testing.T) {
	tests := []struct {
		name       string
		setup      func() *HaCounter
		labels     map[string]string
		wantError  bool
		checkLabel func(*testing.T, *HaCounter)
	}{
		{
			name: "update valid label",
			setup: func() *HaCounter {
				return NewHaCounter("test_counter", "test help", "label1")
			},
			labels:    map[string]string{"label1": "value1"},
			wantError: false,
			checkLabel: func(t *testing.T, c *HaCounter) {
				assert.Equal(t, "value1", c.labelValues["label1"])
			},
		},
		{
			name: "update multiple labels",
			setup: func() *HaCounter {
				return NewHaCounter("test_counter", "test help", "label1", "label2")
			},
			labels:    map[string]string{"label1": "value1", "label2": "value2"},
			wantError: false,
			checkLabel: func(t *testing.T, c *HaCounter) {
				assert.Equal(t, "value1", c.labelValues["label1"])
				assert.Equal(t, "value2", c.labelValues["label2"])
			},
		},
		{
			name: "update with invalid label name",
			setup: func() *HaCounter {
				return NewHaCounter("test_counter", "test help", "label1")
			},
			labels:    map[string]string{"invalid_label": "value1"},
			wantError: true,
		},
		{
			name: "update counter without labels",
			setup: func() *HaCounter {
				return NewHaCounter("test_counter", "test help")
			},
			labels:    map[string]string{"label1": "value1"},
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			counter := tt.setup()
			result := counter.UpdateLabel(tt.labels)

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

func TestHaCounter_Reset(t *testing.T) {
	t.Run("reset after Inc clears label values", func(t *testing.T) {
		counter := createTestCounter("test_counter_reset1", "test help", "label1", "label2")

		counter.UpdateLabel(map[string]string{
			"label1": "value1",
			"label2": "value2",
		})

		assert.Equal(t, "value1", counter.labelValues["label1"])
		assert.Equal(t, "value2", counter.labelValues["label2"])

		err := counter.Inc()
		require.NoError(t, err)

		assert.Equal(t, "", counter.labelValues["label1"])
		assert.Equal(t, "", counter.labelValues["label2"])
		assert.Nil(t, counter.Error)
	})

	t.Run("reset after Add clears label values", func(t *testing.T) {
		counter := createTestCounter("test_counter_reset2", "test help", "label1")

		counter.UpdateLabel(map[string]string{"label1": "value1"})
		assert.Equal(t, "value1", counter.labelValues["label1"])

		err := counter.Add(10.0)
		require.NoError(t, err)

		assert.Equal(t, "", counter.labelValues["label1"])
		assert.Nil(t, counter.Error)
	})

	t.Run("reset clears error state", func(t *testing.T) {
		counter := createTestCounter("test_counter_reset3", "test help", "label1")

		counter.UpdateLabel(map[string]string{"invalid": "value"})
		assert.NotNil(t, counter.Error)

		counter.reset()

		assert.Nil(t, counter.Error)
		assert.Equal(t, "", counter.labelValues["label1"])
	})

	t.Run("multiple operations with reset", func(t *testing.T) {
		counter := createTestCounter("test_counter_reset4", "test help", "topic")

		counter.UpdateLabel(map[string]string{"topic": "topic1"})
		err := counter.Inc()
		require.NoError(t, err)
		assert.Equal(t, "", counter.labelValues["topic"])

		counter.UpdateLabel(map[string]string{"topic": "topic2"})
		err = counter.Add(5.0)
		require.NoError(t, err)
		assert.Equal(t, "", counter.labelValues["topic"])

		counter.UpdateLabel(map[string]string{"topic": "topic3"})
		err = counter.Inc()
		require.NoError(t, err)
		assert.Equal(t, "", counter.labelValues["topic"])
	})
}

func TestHaCounter_WithLabels(t *testing.T) {
	counter := createTestCounter("test_bound_counter", "help", "method", "path")
	bound := counter.WithLabels(map[string]string{"method": "GET", "path": "/api"})
	require.NotNil(t, bound)
	require.NoError(t, bound.Inc())
	require.NoError(t, bound.Inc())
	require.NoError(t, bound.Add(3))
	// Bound with nil labels (no-label counter) just forwards to counter
	noLabelCounter := createTestCounter("test_no_label", "help")
	boundNoLabel := noLabelCounter.WithLabels(nil)
	require.NoError(t, boundNoLabel.Inc())
}
