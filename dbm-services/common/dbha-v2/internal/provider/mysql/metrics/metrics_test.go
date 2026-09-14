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

package mysqlmetrics

import "testing"

func TestMySQLMetricNames(t *testing.T) {
	want := map[string]*struct{}{
		"mysql_cluster_switching_time_consuming_ms":  nil,
		"mysql_host_switching_time_consuming_ms":     nil,
		"mysql_instance_switching_time_consuming_ms": nil,
		"mysql_switching_success_total":              nil,
		"mysql_switching_error_total":                nil,
	}
	got := []string{
		ClusterSwitchingTimeConsumingMs.ToMetric().Name,
		HostSwitchingTimeConsumingMs.ToMetric().Name,
		InstanceSwitchingTimeConsumingMs.ToMetric().Name,
		SwitchingSuccessTotal.ToMetric().Name,
		SwitchingErrorTotal.ToMetric().Name,
	}
	if len(got) != len(want) {
		t.Fatalf("got %d metrics, want %d", len(got), len(want))
	}
	for _, name := range got {
		if _, ok := want[name]; !ok {
			t.Errorf("unexpected metric name %q", name)
		}
		delete(want, name)
	}
	for name := range want {
		t.Errorf("missing metric name %q", name)
	}
}
