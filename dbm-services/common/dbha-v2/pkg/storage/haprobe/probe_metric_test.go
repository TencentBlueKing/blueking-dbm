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

package haprobe

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestProbeMetricJSONRoundTrip(t *testing.T) {
	in := &ProbeMetric{
		Version:         "1.2.3",
		GitTag:          "v1.2.3",
		GitHash:         "abc123",
		BuildTime:       "2026-01-01",
		Pid:             42,
		NumCPU:          8,
		CpuUsagePercent: 12.5,
		MemRssMB:        64,
		MemUsagePercent: 1.5,
		StartedAt:       1700000000,
		UptimeSeconds:   3600,
		Uptime:          "1 hour",
		SampledAt:       1700003600,
	}
	raw, err := json.Marshal(in)
	if err != nil {
		t.Fatalf("marshal failed, errmsg: %s", err)
	}
	var out ProbeMetric
	if err := json.Unmarshal(raw, &out); err != nil {
		t.Fatalf("unmarshal failed, errmsg: %s", err)
	}
	if out != *in {
		t.Errorf("round trip mismatch: got %#v, want %#v", out, *in)
	}
}

func TestProbeMetricZeroNumericFieldsKept(t *testing.T) {
	in := &ProbeMetric{}
	raw, err := json.Marshal(in)
	if err != nil {
		t.Fatalf("marshal failed, errmsg: %s", err)
	}
	text := string(raw)
	for _, key := range []string{
		`"pid"`,
		`"num_cpu"`,
		`"cpu_usage_percent"`,
		`"mem_rss_mb"`,
		`"mem_usage_percent"`,
		`"started_at"`,
		`"uptime_seconds"`,
		`"sampled_at"`,
	} {
		if !strings.Contains(text, key) {
			t.Errorf("missing numeric key %s in %s", key, text)
		}
	}
	for _, key := range []string{
		`"version"`,
		`"git_tag"`,
		`"git_hash"`,
		`"build_time"`,
		`"uptime"`,
	} {
		if strings.Contains(text, key) {
			t.Errorf("empty string key %s should be omitted, got %s", key, text)
		}
	}
}

func TestHarvestDataProbeRoundTrip(t *testing.T) {
	in := &HarvestData{
		HarvestBaseData: HarvestBaseData{
			DbIp: "127.0.0.1",
			Probe: &ProbeMetric{
				Version:         "1.0.0",
				Pid:             7,
				CpuUsagePercent: 0,
				UptimeSeconds:   10,
			},
		},
	}
	raw, err := json.Marshal(in)
	if err != nil {
		t.Fatalf("marshal failed, errmsg: %s", err)
	}
	if !strings.Contains(string(raw), `"probe"`) {
		t.Fatalf("marshaled JSON missing probe key: %s", raw)
	}

	var out HarvestData
	if err := json.Unmarshal(raw, &out); err != nil {
		t.Fatalf("unmarshal failed, errmsg: %s", err)
	}
	if out.Probe == nil {
		t.Fatal("Probe is nil after custom UnmarshalJSON")
	}
	if out.Probe.Version != "1.0.0" || out.Probe.Pid != 7 || out.Probe.UptimeSeconds != 10 {
		t.Errorf("unexpected probe after round trip: %#v", out.Probe)
	}

	nilProbe := &HarvestData{HarvestBaseData: HarvestBaseData{DbIp: "127.0.0.1"}}
	rawNil, err := json.Marshal(nilProbe)
	if err != nil {
		t.Fatalf("marshal nil probe failed, errmsg: %s", err)
	}
	if strings.Contains(string(rawNil), `"probe"`) {
		t.Errorf("nil probe should be omitted, got %s", rawNil)
	}
}
