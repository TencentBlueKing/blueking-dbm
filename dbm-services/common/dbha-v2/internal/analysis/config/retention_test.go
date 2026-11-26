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
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/spf13/viper"
)

func defaultWorkflowForRetention() WorkflowConfig {
	return WorkflowConfig{
		UpdateDbmCacheInterval:     10 * time.Second,
		ReadDbMetaOffsetDuration:   -24 * time.Hour,
		ReadDbMetricOffsetDuration: -60 * time.Second,
		Retention:                  DefaultRetentionConfig(),
	}
}

// unmarshalLikeRun decodes yaml into a Configuration pre-filled with defaults, the same way
// analysis Run decodes into config.Cfg.
func unmarshalLikeRun(t *testing.T, yaml string) Configuration {
	t.Helper()

	path := filepath.Join(t.TempDir(), "analysis.yaml")
	if err := os.WriteFile(path, []byte(yaml), 0o600); err != nil {
		t.Fatalf("write config failed, errmsg: %s", err)
	}

	v := viper.New()
	v.SetConfigFile(path)
	if err := v.ReadInConfig(); err != nil {
		t.Fatalf("read config failed, errmsg: %s", err)
	}

	cfg := Configuration{Workflow: WorkflowConfig{Retention: DefaultRetentionConfig()}}
	if err := v.Unmarshal(&cfg); err != nil {
		t.Fatalf("unmarshal config failed, errmsg: %s", err)
	}

	return cfg
}

func TestRetentionDefaultsAreValid(t *testing.T) {
	got := NormalizeRetention(defaultWorkflowForRetention())
	if got != DefaultRetentionConfig() {
		t.Fatalf("defaults changed by normalization, got: %+v", got)
	}
	if !got.Enabled || got.MetadataRetention != 14*24*time.Hour || got.StatusRetention != 14*24*time.Hour {
		t.Fatalf("unexpected defaults: %+v", got)
	}
	if Cfg.Workflow.Retention != DefaultRetentionConfig() {
		t.Fatalf("package config does not start with retention defaults: %+v", Cfg.Workflow.Retention)
	}
}

func TestRetentionOldConfigWithoutBlockUsesDefaults(t *testing.T) {
	cfg := unmarshalLikeRun(t, minimalAnalysisYAML)
	if cfg.Workflow.Retention != DefaultRetentionConfig() {
		t.Fatalf("old config should keep retention defaults, got: %+v", cfg.Workflow.Retention)
	}
}

func TestRetentionPartialBlockKeepsOtherDefaults(t *testing.T) {
	const scanInterval = "  scanInterval: 3s\n"
	yaml := strings.Replace(minimalAnalysisYAML, scanInterval,
		scanInterval+"  retention:\n    enabled: false\n    interval: 3h\n", 1)

	cfg := unmarshalLikeRun(t, yaml)
	want := DefaultRetentionConfig()
	want.Enabled = false
	want.Interval = 3 * time.Hour
	if cfg.Workflow.Retention != want {
		t.Fatalf("partial retention block, got: %+v, want: %+v", cfg.Workflow.Retention, want)
	}
}

func TestRetentionAgeBoundedByReadWindows(t *testing.T) {
	wf := defaultWorkflowForRetention()
	wf.Retention.MetadataRetention = time.Hour
	wf.Retention.StatusRetention = 0

	got := NormalizeRetention(wf)
	if got.MetadataRetention != 14*24*time.Hour || got.StatusRetention != 14*24*time.Hour {
		t.Fatalf("too small retention should fall back to default, got: %s/%s",
			got.MetadataRetention, got.StatusRetention)
	}

	wf = defaultWorkflowForRetention()
	wf.ReadDbMetaOffsetDuration = -30 * 24 * time.Hour
	got = NormalizeRetention(wf)
	if got.MetadataRetention != 30*24*time.Hour {
		t.Fatalf("retention must not be shorter than the metadata read window, got: %s", got.MetadataRetention)
	}

	wf = defaultWorkflowForRetention()
	wf.Retention.MetadataRetention = 48 * time.Hour
	got = NormalizeRetention(wf)
	if got.MetadataRetention != 48*time.Hour {
		t.Fatalf("valid custom retention must be kept, got: %s", got.MetadataRetention)
	}
}

func TestRetentionHealthWindowsFollowWriters(t *testing.T) {
	wf := defaultWorkflowForRetention()
	wf.UpdateDbmCacheInterval = 20 * time.Minute
	wf.ReadDbMetricOffsetDuration = -5 * time.Minute

	got := NormalizeRetention(wf)
	if got.MetadataHealthWindow != time.Hour {
		t.Fatalf("metadata health window must cover 3 sync intervals, got: %s", got.MetadataHealthWindow)
	}
	if got.StatusHealthWindow != 15*time.Minute {
		t.Fatalf("status health window must cover 3 status read windows, got: %s", got.StatusHealthWindow)
	}
}

func TestRetentionTimeoutPairs(t *testing.T) {
	wf := defaultWorkflowForRetention()
	wf.Retention.SlowDeleteThreshold = 20 * time.Second
	wf.Retention.ScanTimeout = 90 * time.Second

	got := NormalizeRetention(wf)
	def := DefaultRetentionConfig()
	if got.SlowDeleteThreshold != def.SlowDeleteThreshold || got.DeleteTimeout != def.DeleteTimeout {
		t.Fatalf("slow delete threshold must stay below delete timeout, got: %s/%s",
			got.SlowDeleteThreshold, got.DeleteTimeout)
	}
	if got.ScanTimeout != def.ScanTimeout || got.RoundTimeBudget != def.RoundTimeBudget {
		t.Fatalf("scan timeout must stay below round budget, got: %s/%s", got.ScanTimeout, got.RoundTimeBudget)
	}
}

func TestRetentionSizes(t *testing.T) {
	def := DefaultRetentionConfig()
	cases := []struct {
		name                     string
		batch, maxRows, scanRows int
		wantDefault              bool
	}{
		{name: "valid custom", batch: 100, maxRows: 2000, scanRows: 5000},
		{name: "batch above round", batch: 3000, maxRows: 2000, scanRows: 5000, wantDefault: true},
		{name: "round above window", batch: 100, maxRows: 6000, scanRows: 5000, wantDefault: true},
		{name: "window too small", batch: 100, maxRows: 500, scanRows: 500, wantDefault: true},
		{name: "window too large", batch: 100, maxRows: 2000, scanRows: 200000, wantDefault: true},
		{name: "zero batch", batch: 0, maxRows: 2000, scanRows: 5000, wantDefault: true},
		{name: "batch placeholder cap", batch: 14000, maxRows: 14000, scanRows: 20000, wantDefault: true},
		{name: "batch under placeholder cap", batch: 13106, maxRows: 13106, scanRows: 20000},
	}

	for _, c := range cases {
		wf := defaultWorkflowForRetention()
		wf.Retention.BatchSize, wf.Retention.MaxRowsPerRound, wf.Retention.ScanWindowRows = c.batch, c.maxRows, c.scanRows
		got := NormalizeRetention(wf)

		want := [3]int{c.batch, c.maxRows, c.scanRows}
		if c.wantDefault {
			want = [3]int{def.BatchSize, def.MaxRowsPerRound, def.ScanWindowRows}
		}
		if [3]int{got.BatchSize, got.MaxRowsPerRound, got.ScanWindowRows} != want {
			t.Fatalf("%s: got %d/%d/%d, want %v", c.name, got.BatchSize, got.MaxRowsPerRound, got.ScanWindowRows, want)
		}
	}
}

func TestRetentionNonPositiveDurations(t *testing.T) {
	wf := defaultWorkflowForRetention()
	wf.Retention.Interval = 0
	wf.Retention.DrainInterval = -time.Second
	wf.Retention.HealthCheckTimeout = 0
	wf.Retention.StallAlertAfter = 0
	wf.Retention.BatchSleep = -time.Second

	if got := NormalizeRetention(wf); got != DefaultRetentionConfig() {
		t.Fatalf("non-positive durations should fall back to defaults, got: %+v", got)
	}
}
