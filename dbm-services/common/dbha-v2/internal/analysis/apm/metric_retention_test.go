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

package apm

import (
	"testing"
)

func TestRetentionMetricsRegisteredOnce(t *testing.T) {
	want := []string{
		"retention_enabled",
		"retention_leader",
		"retention_deleted_rows_total",
		"retention_attempted_rows_total",
		"retention_skipped_total",
		"retention_errors_total",
		"retention_statement_time_consuming_ms",
		"retention_round_time_consuming_ms",
		"retention_pass_stale_rows",
		"retention_pass_scanned_rows",
		"retention_last_pass_completed_timestamp_seconds",
		"retention_stalled",
	}

	names := map[string]bool{}
	for _, name := range FrameworkMetricNames() {
		names[name] = true
	}
	for _, name := range want {
		if !names[name] {
			t.Fatalf("retention metric %s is not registered as a framework metric", name)
		}
	}

	if got := len(frameworkMetrics()); got != len(FrameworkMetricNames()) {
		t.Fatalf("framework metrics contain duplicate names, metrics: %d, unique names: %d",
			got, len(FrameworkMetricNames()))
	}
}
