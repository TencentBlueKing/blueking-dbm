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

func createTestSummary(name, help string, labelNames ...string) *HaSummary {
	summary := NewHaSummary(name, help, labelNames...)
	summary.metric.Collector = newCollector(summary.ToMetric(), "dbha-v2-test")
	return summary
}

func TestNewHaSummary(t *testing.T) {
	tests := []struct {
		name       string
		metricName string
		help       string
		labelNames []string
		wantType   string
	}{
		{
			name:       "summary without labels",
			metricName: "test_summary",
			help:       "test summary help",
			labelNames: nil,
			wantType:   MetricTypeSummary.String(),
		},
		{
			name:       "summary with single label",
			metricName: "test_summary_vec",
			help:       "test summary vec help",
			labelNames: []string{"label1"},
			wantType:   MetricTypeSummaryVec.String(),
		},
		{
			name:       "summary with multiple labels",
			metricName: "test_summary_multi",
			help:       "test summary multi help",
			labelNames: []string{"label1", "label2", "label3"},
			wantType:   MetricTypeSummaryVec.String(),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			summary := NewHaSummary(tt.metricName, tt.help, tt.labelNames...)

			require.NotNil(t, summary)
			require.NotNil(t, summary.metric)
			assert.Equal(t, tt.metricName, summary.metric.Name)
			assert.Equal(t, tt.help, summary.metric.Description)
			assert.Equal(t, tt.wantType, summary.metric.Type)
			assert.Equal(t, tt.labelNames, summary.labelNames)

			if len(tt.labelNames) > 0 {
				require.NotNil(t, summary.labelValues)
				assert.Equal(t, len(tt.labelNames), len(summary.labelValues))
				for _, name := range tt.labelNames {
					assert.Equal(t, "", summary.labelValues[name])
				}
			}
		})
	}
}

func TestHaSummary_Observe(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaSummary
		value     float64
		wantError bool
	}{
		{
			name: "observe without labels",
			setup: func() *HaSummary {
				return createTestSummary("test_summary_observe", "test help")
			},
			value:     42.5,
			wantError: false,
		},
		{
			name: "observe with valid labels",
			setup: func() *HaSummary {
				summary := createTestSummary("test_summary_observe_vec", "test help", "label1")
				summary.UpdateLabel(map[string]string{"label1": "value1"})
				return summary
			},
			value:     100.0,
			wantError: false,
		},
		{
			name: "observe with missing labels",
			setup: func() *HaSummary {
				summary := createTestSummary("test_summary_observe_missing", "test help", "label1")
				summary.UpdateLabel(map[string]string{"label1": "value1"})
				summary.UpdateLabel(map[string]string{"label2": "value2"})
				return summary
			},
			value:     50.0,
			wantError: true,
		},
		{
			name: "observe zero value",
			setup: func() *HaSummary {
				return createTestSummary("test_summary_observe_zero", "test help")
			},
			value:     0.0,
			wantError: false,
		},
		{
			name: "observe negative value",
			setup: func() *HaSummary {
				return createTestSummary("test_summary_observe_negative", "test help")
			},
			value:     -10.5,
			wantError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			summary := tt.setup()
			err := summary.Observe(tt.value)

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaSummary_UpdateLabel(t *testing.T) {
	tests := []struct {
		name       string
		setup      func() *HaSummary
		labels     map[string]string
		wantError  bool
		checkLabel func(*testing.T, *HaSummary)
	}{
		{
			name: "update valid label",
			setup: func() *HaSummary {
				return NewHaSummary("test_summary", "test help", "label1")
			},
			labels:    map[string]string{"label1": "value1"},
			wantError: false,
			checkLabel: func(t *testing.T, s *HaSummary) {
				assert.Equal(t, "value1", s.labelValues["label1"])
			},
		},
		{
			name: "update multiple labels",
			setup: func() *HaSummary {
				return NewHaSummary("test_summary", "test help", "label1", "label2")
			},
			labels:    map[string]string{"label1": "value1", "label2": "value2"},
			wantError: false,
			checkLabel: func(t *testing.T, s *HaSummary) {
				assert.Equal(t, "value1", s.labelValues["label1"])
				assert.Equal(t, "value2", s.labelValues["label2"])
			},
		},
		{
			name: "update with invalid label name",
			setup: func() *HaSummary {
				return NewHaSummary("test_summary", "test help", "label1")
			},
			labels:    map[string]string{"invalid_label": "value1"},
			wantError: true,
		},
		{
			name: "update summary without labels",
			setup: func() *HaSummary {
				return NewHaSummary("test_summary", "test help")
			},
			labels:    map[string]string{"label1": "value1"},
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			summary := tt.setup()
			result := summary.UpdateLabel(tt.labels)

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

func TestHaSummary_Reset(t *testing.T) {
	t.Run("reset after Observe clears label values", func(t *testing.T) {
		summary := createTestSummary("test_summary_reset1", "test help", "label1", "label2")

		summary.UpdateLabel(map[string]string{
			"label1": "value1",
			"label2": "value2",
		})

		assert.Equal(t, "value1", summary.labelValues["label1"])
		assert.Equal(t, "value2", summary.labelValues["label2"])

		err := summary.Observe(42.5)
		require.NoError(t, err)

		assert.Equal(t, "", summary.labelValues["label1"])
		assert.Equal(t, "", summary.labelValues["label2"])
		assert.Nil(t, summary.Error)
	})

	t.Run("reset clears error state", func(t *testing.T) {
		summary := createTestSummary("test_summary_reset2", "test help", "label1")

		summary.UpdateLabel(map[string]string{"invalid": "value"})
		assert.NotNil(t, summary.Error)

		summary.reset()
		assert.Nil(t, summary.Error)
		assert.Equal(t, "", summary.labelValues["label1"])
	})

	t.Run("multiple observations with reset", func(t *testing.T) {
		summary := createTestSummary("test_summary_reset3", "test help", "endpoint")

		summary.UpdateLabel(map[string]string{"endpoint": "/api/v1"})
		err := summary.Observe(10.5)
		require.NoError(t, err)
		assert.Equal(t, "", summary.labelValues["endpoint"])

		summary.UpdateLabel(map[string]string{"endpoint": "/api/v2"})
		err = summary.Observe(25.3)
		require.NoError(t, err)
		assert.Equal(t, "", summary.labelValues["endpoint"])

		summary.UpdateLabel(map[string]string{"endpoint": "/api/v3"})
		err = summary.Observe(50.0)
		require.NoError(t, err)
		assert.Equal(t, "", summary.labelValues["endpoint"])
	})
}

func TestHaSummary_MultipleObservations(t *testing.T) {
	t.Run("multiple observations with same labels", func(t *testing.T) {
		summary := createTestSummary("test_summary_multiple", "test help", "method")

		values := []float64{10.5, 20.3, 30.7, 40.2, 50.9}
		for _, val := range values {
			summary.UpdateLabel(map[string]string{"method": "GET"})
			err := summary.Observe(val)
			assert.NoError(t, err)
		}
	})

	t.Run("observations with different label values", func(t *testing.T) {
		summary := createTestSummary("test_summary_diff_labels", "test help", "status")

		testCases := []struct {
			labelValue   string
			observeValue float64
		}{
			{"200", 10.5},
			{"404", 5.2},
			{"500", 100.3},
			{"200", 8.7},
		}

		for _, tc := range testCases {
			summary.UpdateLabel(map[string]string{"status": tc.labelValue})
			err := summary.Observe(tc.observeValue)
			assert.NoError(t, err)
		}
	})
}
