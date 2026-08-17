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

package selfmetric

import (
	"context"
	"encoding/json"
	"math"
	"os"
	"runtime"
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/version"
)

func TestCpuUsagePercent(t *testing.T) {
	base := time.Unix(1_700_000_000, 0)
	cases := []struct {
		name string
		prev sample
		cur  sample
		want float64
	}{
		{
			name: "normal 50 percent",
			prev: sample{cpuSeconds: 1.0, takenAt: base},
			cur:  sample{cpuSeconds: 1.5, takenAt: base.Add(time.Second)},
			want: 50,
		},
		{
			name: "wall clock not advanced",
			prev: sample{cpuSeconds: 1.0, takenAt: base},
			cur:  sample{cpuSeconds: 2.0, takenAt: base},
			want: 0,
		},
		{
			name: "wall clock negative",
			prev: sample{cpuSeconds: 1.0, takenAt: base.Add(time.Second)},
			cur:  sample{cpuSeconds: 2.0, takenAt: base},
			want: 0,
		},
		{
			name: "cpu counter went backwards",
			prev: sample{cpuSeconds: 2.0, takenAt: base},
			cur:  sample{cpuSeconds: 1.0, takenAt: base.Add(time.Second)},
			want: 0,
		},
		{
			name: "multi core over 100",
			prev: sample{cpuSeconds: 0, takenAt: base},
			cur:  sample{cpuSeconds: 2.0, takenAt: base.Add(time.Second)},
			want: 200,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := cpuUsagePercent(tc.prev, tc.cur)
			if got != tc.want {
				t.Errorf("got %v, want %v", got, tc.want)
			}
			if math.IsInf(got, 0) || math.IsNaN(got) {
				t.Errorf("got non-finite value: %v", got)
			}
		})
	}
}

func TestCpuUsageSinceStart(t *testing.T) {
	cases := []struct {
		name       string
		cpuSeconds float64
		uptime     time.Duration
		want       float64
	}{
		{name: "normal", cpuSeconds: 0.5, uptime: 10 * time.Second, want: 5},
		{name: "zero uptime", cpuSeconds: 0.5, uptime: 0, want: 0},
		{name: "negative uptime", cpuSeconds: 0.5, uptime: -time.Second, want: 0},
		{name: "zero cpu", cpuSeconds: 0, uptime: 10 * time.Second, want: 0},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := cpuUsageSinceStart(tc.cpuSeconds, tc.uptime)
			if got != tc.want {
				t.Errorf("got %v, want %v", got, tc.want)
			}
			if math.IsInf(got, 0) || math.IsNaN(got) {
				t.Errorf("got non-finite value: %v", got)
			}
		})
	}
}

func TestSnapshotNeverInfOrNaN(t *testing.T) {
	base := time.Unix(1_700_000_000, 0)
	values := []float64{
		cpuUsagePercent(sample{0, base}, sample{0.5, base.Add(time.Second)}),
		cpuUsagePercent(sample{1, base}, sample{1, base}),
		cpuUsageSinceStart(1, 0),
		cpuUsageSinceStart(1, -time.Second),
		cpuUsageSinceStart(0.5, 10*time.Second),
	}
	for _, v := range values {
		if math.IsInf(v, 0) || math.IsNaN(v) {
			t.Fatalf("non-finite cpu percent: %v", v)
		}
	}

	s, err := newSampler()
	if err != nil {
		t.Fatalf("newSampler failed, errmsg: %s", err)
	}
	s.sampleOnce()
	snap := s.snapshot()
	if snap == nil {
		t.Fatal("snapshot is nil after sampleOnce")
	}
	if _, err := json.Marshal(snap); err != nil {
		t.Fatalf("json.Marshal snapshot failed, errmsg: %s", err)
	}
	if math.IsInf(snap.CpuUsagePercent, 0) || math.IsNaN(snap.CpuUsagePercent) {
		t.Errorf("CpuUsagePercent non-finite: %v", snap.CpuUsagePercent)
	}
	if math.IsInf(snap.MemUsagePercent, 0) || math.IsNaN(snap.MemUsagePercent) {
		t.Errorf("MemUsagePercent non-finite: %v", snap.MemUsagePercent)
	}
}

func TestSnapshotBeforeFirstSample(t *testing.T) {
	s, err := newSampler()
	if err != nil {
		t.Fatalf("newSampler failed, errmsg: %s", err)
	}
	if got := s.snapshot(); got != nil {
		t.Errorf("snapshot before sample = %#v, want nil", got)
	}
}

func TestSamplerFillsFields(t *testing.T) {
	s, err := newSampler()
	if err != nil {
		t.Fatalf("newSampler failed, errmsg: %s", err)
	}
	s.sampleOnce()
	snap := s.snapshot()
	if snap == nil {
		t.Fatal("snapshot is nil")
	}
	if snap.Version != version.Get().Version {
		t.Errorf("Version = %q, want %q", snap.Version, version.Get().Version)
	}
	if snap.Pid != int32(os.Getpid()) {
		t.Errorf("Pid = %d, want %d", snap.Pid, os.Getpid())
	}
	if snap.NumCPU != runtime.NumCPU() {
		t.Errorf("NumCPU = %d, want %d", snap.NumCPU, runtime.NumCPU())
	}
	if snap.SampledAt == 0 {
		t.Error("SampledAt is 0")
	}
	if snap.Uptime == "" && snap.UptimeSeconds == 0 {
		// Brand-new process may still have 0 seconds; Uptime string may be empty.
		t.Log("uptime still zero; acceptable for very young process")
	}
}

func TestRunStopsOnContextCancel(t *testing.T) {
	s, err := newSampler()
	if err != nil {
		t.Fatalf("newSampler failed, errmsg: %s", err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		s.run(ctx, make(chan struct{}), 10*time.Millisecond)
		close(done)
	}()
	cancel()
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("run did not stop on context cancel")
	}
}

func TestRunStopsOnQuit(t *testing.T) {
	s, err := newSampler()
	if err != nil {
		t.Fatalf("newSampler failed, errmsg: %s", err)
	}
	quit := make(chan struct{})
	done := make(chan struct{})
	go func() {
		s.run(context.Background(), quit, 10*time.Millisecond)
		close(done)
	}()
	close(quit)
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("run did not stop on quit")
	}
}

func TestRunSamplesImmediately(t *testing.T) {
	s, err := newSampler()
	if err != nil {
		t.Fatalf("newSampler failed, errmsg: %s", err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	quit := make(chan struct{})
	go s.run(ctx, quit, time.Hour)

	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if s.snapshot() != nil {
			close(quit)
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	close(quit)
	t.Fatal("snapshot still nil after immediate sample window")
}

func TestSnapshotIsCopy(t *testing.T) {
	s, err := newSampler()
	if err != nil {
		t.Fatalf("newSampler failed, errmsg: %s", err)
	}
	s.sampleOnce()
	first := s.snapshot()
	first.CpuUsagePercent = -1
	second := s.snapshot()
	if second.CpuUsagePercent == -1 {
		t.Fatal("mutating snapshot copy affected stored snapshot")
	}
}

func TestConcurrentSnapshot(t *testing.T) {
	s, err := newSampler()
	if err != nil {
		t.Fatalf("newSampler failed, errmsg: %s", err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	quit := make(chan struct{})
	go s.run(ctx, quit, 10*time.Millisecond)

	var wg sync.WaitGroup
	for i := 0; i < 8; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 50; j++ {
				_ = s.snapshot()
			}
		}()
	}
	wg.Wait()
	close(quit)
}

func TestRunTwiceIsSafe(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	quit := make(chan struct{})

	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		Run(ctx, quit)
	}()
	go func() {
		defer wg.Done()
		Run(ctx, quit)
	}()

	time.Sleep(50 * time.Millisecond)
	close(quit)
	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(3 * time.Second):
		t.Fatal("Run did not return after quit")
	}
}
