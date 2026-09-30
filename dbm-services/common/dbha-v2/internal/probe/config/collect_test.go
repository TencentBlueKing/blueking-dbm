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

package config

import (
	"testing"
	"time"
)

// TestCollectTaskCountUsesConfiguredValue pins the rule that the configured
// worker count is used as-is: only a non-positive value falls back to the
// default, and the value is deliberately NOT aligned to a granularity multiple.
func TestCollectTaskCountUsesConfiguredValue(t *testing.T) {
	cases := []struct {
		name string
		in   int
		want int
	}{
		{name: "zero falls back to the default", in: 0, want: defaultCollectTaskGoroutines},
		{name: "negative falls back to the default", in: -1, want: defaultCollectTaskGoroutines},
		{name: "one is used as-is", in: 1, want: 1},
		{name: "eight is used as-is", in: 8, want: 8},
		{name: "ten is not aligned up to sixteen", in: 10, want: 10},
		{name: "twenty is not aligned up to twenty four", in: 20, want: 20},
		{name: "thirty two is used as-is", in: 32, want: 32},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			c := CollectConfig{CollectTaskGoroutines: tc.in}
			if got := c.CollectTaskCount(); got != tc.want {
				t.Errorf("CollectTaskCount() = %d, want %d", got, tc.want)
			}
		})
	}
}

func TestClampCollect(t *testing.T) {
	cfg := Configuration{Collect: CollectConfig{CollectTaskGoroutines: 10}}
	clampCollect(&cfg)
	if cfg.Collect.CollectTaskGoroutines != 10 {
		t.Errorf("collect task count after clamp = %d, want 10 (used as-is)",
			cfg.Collect.CollectTaskGoroutines)
	}

	// An unset block must stay zero, otherwise a probe.yaml written before the
	// block existed would gain it on the next render.
	unset := Configuration{}
	clampCollect(&unset)
	if unset.Collect.CollectTaskGoroutines != 0 {
		t.Errorf("an unset collect task count must stay zero, got: %d", unset.Collect.CollectTaskGoroutines)
	}
	if !unset.Collect.IsZero() {
		t.Errorf("an unset collect block must stay zero, got: %+v", unset.Collect)
	}
}

func TestCollectConfigEffectiveValues(t *testing.T) {
	var empty CollectConfig
	if got := empty.CollectTaskCount(); got != defaultCollectTaskGoroutines {
		t.Errorf("CollectTaskCount() = %d, want %d", got, defaultCollectTaskGoroutines)
	}
	set := CollectConfig{CollectTaskGoroutines: 20}
	if got := set.CollectTaskCount(); got != 20 {
		t.Errorf("CollectTaskCount() = %d, want 20", got)
	}
}

func TestHostMetricIntervalEffectiveValues(t *testing.T) {
	var empty CollectConfig
	if got := empty.HostMetricIntervalDuration(); got != defaultHostMetricInterval {
		t.Errorf("HostMetricIntervalDuration() = %v, want %v", got, defaultHostMetricInterval)
	}

	set := CollectConfig{HostMetricInterval: 30 * time.Second}
	if got := set.HostMetricIntervalDuration(); got != 30*time.Second {
		t.Errorf("HostMetricIntervalDuration() = %v, want 30s", got)
	}
}

// TestWithCollectKeepsLocalValues guards the round trip: admin never sends the
// collect block, so it survives only through LocalFields.
func TestWithCollectKeepsLocalValues(t *testing.T) {
	local := Configuration{
		Collect: CollectConfig{CollectTaskGoroutines: 24},
	}

	rendered, err := GenProbeYAML(newMirrorPayload(), LocalFields(local)...)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}

	parsed, err := ParseBytes([]byte(rendered))
	if err != nil {
		t.Fatalf("rendered config does not parse, errmsg: %s", err)
	}
	if parsed.Collect != local.Collect {
		t.Errorf("collect block lost, got: %+v, want: %+v", parsed.Collect, local.Collect)
	}
}

func TestWithCollectSkipsZeroBlock(t *testing.T) {
	rendered, err := GenProbeYAML(newMirrorPayload(), LocalFields(Configuration{})...)
	if err != nil {
		t.Fatalf("GenProbeYAML failed, errmsg: %s", err)
	}
	if containsSeq(rendered, "collect:") {
		t.Error("a zero-valued collect block should not be rendered")
	}
}

// containsSeq reports whether s contains sub.
func containsSeq(s, sub string) bool {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
