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

package workflow

import (
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// retentionMetrics is the reporting surface of the retainer, kept narrow so tests can record calls.
type retentionMetrics interface {
	enabled(on bool)
	elected(tables []string, at time.Time)
	lost()
	statement(table, stage string, elapsed time.Duration)
	round(table string, elapsed time.Duration)
	skipped(table, reason string)
	failed(table, stage, kind string)
	attempted(table string, rows int)
	deleted(table string, rows int64)
	passCompleted(table string, staleRows, scannedRows int64, at time.Time)
	stalled(table string, on bool)
}

// apmRetentionMetrics reports retention metrics through the analysis APM collectors. Reporting
// failures are logged and never interrupt the cleanup.
type apmRetentionMetrics struct {
	serviceID string
}

func newApmRetentionMetrics(serviceID string) *apmRetentionMetrics {
	return &apmRetentionMetrics{serviceID: serviceID}
}

func (m *apmRetentionMetrics) enabled(on bool) {
	m.setGauge(apm.RetentionEnabled, m.labels(), retentionBoolToFloat(on))
}

// elected marks this instance as leader and starts both the stall timer and the pass-completion
// timer at the election time, so a pass that never completes still raises an alert.
func (m *apmRetentionMetrics) elected(tables []string, at time.Time) {
	m.setGauge(apm.RetentionLeader, m.labels(), 1)
	for _, table := range tables {
		m.setGauge(apm.RetentionLastPassCompletedTimestampSeconds, m.tableLabels(table), float64(at.Unix()))
		m.setGauge(apm.RetentionStalled, m.tableLabels(table), 0)
	}
}

// lost drops the state series of this instance so a former leader does not keep stale values.
func (m *apmRetentionMetrics) lost() {
	m.setGauge(apm.RetentionLeader, m.labels(), 0)
	apm.RetentionStalled.Clear()
	apm.RetentionPassStaleRows.Clear()
	apm.RetentionPassScannedRows.Clear()
	apm.RetentionLastPassCompletedTimestampSeconds.Clear()
}

func (m *apmRetentionMetrics) statement(table, stage string, elapsed time.Duration) {
	labels := m.tableLabels(table)
	labels[apm.MetricLabelStage] = stage
	m.observe(apm.RetentionStatementTimeConsumingMs, labels, float64(elapsed.Milliseconds()))
}

func (m *apmRetentionMetrics) round(table string, elapsed time.Duration) {
	m.observe(apm.RetentionRoundTimeConsumingMs, m.tableLabels(table), float64(elapsed.Milliseconds()))
}

func (m *apmRetentionMetrics) skipped(table, reason string) {
	labels := m.tableLabels(table)
	labels[apm.MetricLabelReason] = reason
	m.addCounter(apm.RetentionSkippedTotal, labels, 1)
}

func (m *apmRetentionMetrics) failed(table, stage, kind string) {
	labels := m.tableLabels(table)
	labels[apm.MetricLabelStage] = stage
	labels[apm.MetricLabelKind] = kind
	m.addCounter(apm.RetentionErrorsTotal, labels, 1)
}

func (m *apmRetentionMetrics) attempted(table string, rows int) {
	m.addCounter(apm.RetentionAttemptedRowsTotal, m.tableLabels(table), float64(rows))
}

func (m *apmRetentionMetrics) deleted(table string, rows int64) {
	m.addCounter(apm.RetentionDeletedRowsTotal, m.tableLabels(table), float64(rows))
}

func (m *apmRetentionMetrics) passCompleted(table string, staleRows, scannedRows int64, at time.Time) {
	m.setGauge(apm.RetentionPassStaleRows, m.tableLabels(table), float64(staleRows))
	m.setGauge(apm.RetentionPassScannedRows, m.tableLabels(table), float64(scannedRows))
	m.setGauge(apm.RetentionLastPassCompletedTimestampSeconds, m.tableLabels(table), float64(at.Unix()))
}

func (m *apmRetentionMetrics) stalled(table string, on bool) {
	m.setGauge(apm.RetentionStalled, m.tableLabels(table), retentionBoolToFloat(on))
}

func (m *apmRetentionMetrics) labels() map[string]string {
	return map[string]string{
		haapm.MetricLabelServiceID:   m.serviceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}
}

func (m *apmRetentionMetrics) tableLabels(table string) map[string]string {
	labels := m.labels()
	labels[apm.MetricLabelTable] = table

	return labels
}

func (m *apmRetentionMetrics) setGauge(g *haapm.HaGauge, labels map[string]string, val float64) {
	if err := g.SetWithLabels(labels, val); err != nil {
		logger.Warn("report retention metric failed, metric: %s, errmsg: %s", g.ToMetric().Name, err)
	}
}

func (m *apmRetentionMetrics) addCounter(c *haapm.HaCounter, labels map[string]string, val float64) {
	if err := c.AddWithLabels(labels, val); err != nil {
		logger.Warn("report retention metric failed, metric: %s, errmsg: %s", c.ToMetric().Name, err)
	}
}

func (m *apmRetentionMetrics) observe(h *haapm.HaHistogram, labels map[string]string, val float64) {
	if err := h.ObserveWithLabels(labels, val); err != nil {
		logger.Warn("report retention metric failed, metric: %s, errmsg: %s", h.ToMetric().Name, err)
	}
}

func retentionBoolToFloat(on bool) float64 {
	if on {
		return 1
	}

	return 0
}
