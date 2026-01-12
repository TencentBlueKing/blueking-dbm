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

func createTestGauge(name, help string, labelNames ...string) *HaGauge {
	gauge := NewHaGauge(name, help, labelNames...)

	metricDef := gauge.ToMetric()
	gauge.metric.Collector = metric.NewMetric(metricDef, "dbha-v2-test")
	return gauge
}

func TestNewHaGauge(t *testing.T) {
	tests := []struct {
		name       string
		metricName string
		help       string
		labelNames []string
		wantType   string
	}{
		{
			name:       "gauge without labels",
			metricName: "test_gauge",
			help:       "test gauge help",
			labelNames: nil,
			wantType:   MetricTypeGauge.String(),
		},
		{
			name:       "gauge with single label",
			metricName: "test_gauge_vec",
			help:       "test gauge vec help",
			labelNames: []string{"label1"},
			wantType:   MetricTypeGaugeVec.String(),
		},
		{
			name:       "gauge with multiple labels",
			metricName: "test_gauge_multi",
			help:       "test gauge multi help",
			labelNames: []string{"label1", "label2", "label3"},
			wantType:   MetricTypeGaugeVec.String(),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gauge := NewHaGauge(tt.metricName, tt.help, tt.labelNames...)

			require.NotNil(t, gauge)
			require.NotNil(t, gauge.metric)
			assert.Equal(t, tt.metricName, gauge.metric.Name)
			assert.Equal(t, tt.help, gauge.metric.Description)
			assert.Equal(t, tt.wantType, gauge.metric.Type)
			assert.Equal(t, tt.labelNames, gauge.labelNames)

			if len(tt.labelNames) > 0 {
				require.NotNil(t, gauge.labelValues)
				assert.Equal(t, len(tt.labelNames), len(gauge.labelValues))
				for _, name := range tt.labelNames {
					assert.Equal(t, "", gauge.labelValues[name])
				}
			}
		})
	}
}

func TestHaGauge_Set(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaGauge
		value     float64
		wantError bool
	}{
		{
			name: "set without labels",
			setup: func() *HaGauge {
				return createTestGauge("test_gauge_set", "test help")
			},
			value:     42.5,
			wantError: false,
		},
		{
			name: "set with valid labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_set_vec", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				return gauge
			},
			value:     100.0,
			wantError: false,
		},
		{
			name: "set with missing labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_set_missing", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				gauge.UpdateLabel(map[string]string{"label2": "value2"})
				return gauge
			},
			value:     50.0,
			wantError: true,
		},
		{
			name: "set negative value",
			setup: func() *HaGauge {
				return createTestGauge("test_gauge_set_negative", "test help")
			},
			value:     -10.5,
			wantError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gauge := tt.setup()
			err := gauge.Set(tt.value)

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaGauge_Inc(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaGauge
		wantError bool
	}{
		{
			name: "inc without labels",
			setup: func() *HaGauge {
				return createTestGauge("test_gauge_inc", "test help")
			},
			wantError: false,
		},
		{
			name: "inc with valid labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_inc_vec", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				return gauge
			},
			wantError: false,
		},
		{
			name: "inc with missing labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_inc_missing", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				gauge.UpdateLabel(map[string]string{"label2": "value2"})
				return gauge
			},
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gauge := tt.setup()
			err := gauge.Inc()

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaGauge_Dec(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaGauge
		wantError bool
	}{
		{
			name: "dec without labels",
			setup: func() *HaGauge {
				return createTestGauge("test_gauge_dec", "test help")
			},
			wantError: false,
		},
		{
			name: "dec with valid labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_dec_vec", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				return gauge
			},
			wantError: false,
		},
		{
			name: "dec with missing labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_dec_missing", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				gauge.UpdateLabel(map[string]string{"label2": "value2"})
				return gauge
			},
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gauge := tt.setup()
			err := gauge.Dec()

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaGauge_Add(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaGauge
		value     float64
		wantError bool
	}{
		{
			name: "add without labels",
			setup: func() *HaGauge {
				return createTestGauge("test_gauge_add", "test help")
			},
			value:     10.5,
			wantError: false,
		},
		{
			name: "add with valid labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_add_vec", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				return gauge
			},
			value:     20.3,
			wantError: false,
		},
		{
			name: "add negative value",
			setup: func() *HaGauge {
				return createTestGauge("test_gauge_add_negative", "test help")
			},
			value:     -5.5,
			wantError: false,
		},
		{
			name: "add with missing labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_add_missing", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				gauge.UpdateLabel(map[string]string{"label2": "value2"})
				return gauge
			},
			value:     5.0,
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gauge := tt.setup()
			err := gauge.Add(tt.value)

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaGauge_Sub(t *testing.T) {
	tests := []struct {
		name      string
		setup     func() *HaGauge
		value     float64
		wantError bool
	}{
		{
			name: "sub without labels",
			setup: func() *HaGauge {
				return createTestGauge("test_gauge_sub", "test help")
			},
			value:     10.5,
			wantError: false,
		},
		{
			name: "sub with valid labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_sub_vec", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				return gauge
			},
			value:     20.3,
			wantError: false,
		},
		{
			name: "sub with missing labels",
			setup: func() *HaGauge {
				gauge := createTestGauge("test_gauge_sub_missing", "test help", "label1")
				gauge.UpdateLabel(map[string]string{"label1": "value1"})
				gauge.UpdateLabel(map[string]string{"label2": "value2"})
				return gauge
			},
			value:     5.0,
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gauge := tt.setup()
			err := gauge.Sub(tt.value)

			if tt.wantError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestHaGauge_UpdateLabel(t *testing.T) {
	tests := []struct {
		name       string
		setup      func() *HaGauge
		labels     map[string]string
		wantError  bool
		checkLabel func(*testing.T, *HaGauge)
	}{
		{
			name: "update valid label",
			setup: func() *HaGauge {
				return NewHaGauge("test_gauge", "test help", "label1")
			},
			labels:    map[string]string{"label1": "value1"},
			wantError: false,
			checkLabel: func(t *testing.T, g *HaGauge) {
				assert.Equal(t, "value1", g.labelValues["label1"])
			},
		},
		{
			name: "update multiple labels",
			setup: func() *HaGauge {
				return NewHaGauge("test_gauge", "test help", "label1", "label2")
			},
			labels:    map[string]string{"label1": "value1", "label2": "value2"},
			wantError: false,
			checkLabel: func(t *testing.T, g *HaGauge) {
				assert.Equal(t, "value1", g.labelValues["label1"])
				assert.Equal(t, "value2", g.labelValues["label2"])
			},
		},
		{
			name: "update with invalid label name",
			setup: func() *HaGauge {
				return NewHaGauge("test_gauge", "test help", "label1")
			},
			labels:    map[string]string{"invalid_label": "value1"},
			wantError: true,
		},
		{
			name: "update gauge without labels",
			setup: func() *HaGauge {
				return NewHaGauge("test_gauge", "test help")
			},
			labels:    map[string]string{"label1": "value1"},
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gauge := tt.setup()
			result := gauge.UpdateLabel(tt.labels)

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

func TestHaGauge_Reset(t *testing.T) {
	t.Run("reset after Set does NOT clear label values", func(t *testing.T) {
		gauge := createTestGauge("test_gauge_reset1", "test help", "label1", "label2")

		gauge.UpdateLabel(map[string]string{
			"label1": "value1",
			"label2": "value2",
		})

		assert.Equal(t, "value1", gauge.labelValues["label1"])
		assert.Equal(t, "value2", gauge.labelValues["label2"])

		err := gauge.Set(100.0)
		require.NoError(t, err)

		assert.Equal(t, "value1", gauge.labelValues["label1"])
		assert.Equal(t, "value2", gauge.labelValues["label2"])
		assert.Nil(t, gauge.Error)
	})

	t.Run("reset clears error state only", func(t *testing.T) {
		gauge := createTestGauge("test_gauge_reset2", "test help", "label1")

		gauge.UpdateLabel(map[string]string{"label1": "value1"})
		gauge.UpdateLabel(map[string]string{"invalid": "value"})
		assert.NotNil(t, gauge.Error)

		originalLabelValue := gauge.labelValues["label1"]
		gauge.reset()

		assert.Nil(t, gauge.Error)
		assert.Equal(t, originalLabelValue, gauge.labelValues["label1"])
	})

	t.Run("multiple operations preserve label values", func(t *testing.T) {
		gauge := createTestGauge("test_gauge_reset3", "test help", "service")

		gauge.UpdateLabel(map[string]string{"service": "api"})
		err := gauge.Set(10.0)
		require.NoError(t, err)
		assert.Equal(t, "api", gauge.labelValues["service"])

		err = gauge.Inc()
		require.NoError(t, err)
		assert.Equal(t, "api", gauge.labelValues["service"])

		err = gauge.Add(5.0)
		require.NoError(t, err)
		assert.Equal(t, "api", gauge.labelValues["service"])
	})
}
