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

// Package selfmetric samples the probe process's own version and resource usage.
package selfmetric

import (
	"context"
	"math"
	"os"
	"runtime"
	"sync"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
	"dbm-services/common/dbha-v2/pkg/version"

	"github.com/hako/durafmt"
	gopsutil "github.com/shirou/gopsutil/v3/process"
)

// SampleInterval is the fixed period for probe self-metric sampling.
const SampleInterval = 60 * time.Second

// sample is one raw CPU reading used to derive usage between two ticks.
type sample struct {
	cpuSeconds float64
	takenAt    time.Time
}

// cpuUsagePercent returns single-core based CPU usage between two samples.
// It returns 0 when the wall clock did not advance or the CPU counter went
// backwards (process restart / clock skew), never a negative value, an infinity
// or a NaN.
func cpuUsagePercent(prev, cur sample) float64 {
	elapsed := cur.takenAt.Sub(prev.takenAt).Seconds()
	if elapsed <= 0 {
		return 0
	}
	delta := cur.cpuSeconds - prev.cpuSeconds
	if delta < 0 {
		return 0
	}
	return sanitizePercent(delta / elapsed * 100)
}

// cpuUsageSinceStart returns the average single-core based CPU usage since the
// process started. It is only used for the very first sample, which has no
// predecessor to diff against. It returns 0 for a non-positive uptime, which
// happens when the process is younger than one clock tick.
func cpuUsageSinceStart(cpuSeconds float64, uptime time.Duration) float64 {
	if uptime <= 0 || cpuSeconds < 0 {
		return 0
	}
	return sanitizePercent(cpuSeconds / uptime.Seconds() * 100)
}

func sanitizePercent(v float64) float64 {
	if math.IsInf(v, 0) || math.IsNaN(v) || v < 0 {
		return 0
	}
	return v
}

func toNonNegUint64(v int64) uint64 {
	if v <= 0 {
		return 0
	}
	return uint64(v)
}

func durationToNonNegSeconds(d time.Duration) uint64 {
	if d <= 0 {
		return 0
	}
	return uint64(d / time.Second)
}

// sampler owns the sampling state of one probe process.
type sampler struct {
	proc   *gopsutil.Process
	prev   *sample
	latest atomic.Pointer[haprobe.ProbeMetric]
}

func newSampler() (*sampler, error) {
	proc, err := gopsutil.NewProcess(int32(os.Getpid()))
	if err != nil {
		return nil, err
	}
	return &sampler{proc: proc}, nil
}

func (s *sampler) snapshot() *haprobe.ProbeMetric {
	cur := s.latest.Load()
	if cur == nil {
		return nil
	}
	cp := *cur
	return &cp
}

func (s *sampler) takeCPUSample() (sample, error) {
	times, err := s.proc.Times()
	if err != nil {
		return sample{}, err
	}
	return sample{
		cpuSeconds: times.User + times.System,
		takenAt:    time.Now(),
	}, nil
}

func (s *sampler) sampleOnce() {
	metric := &haprobe.ProbeMetric{}
	info := version.Get()
	metric.Version = info.Version
	metric.GitTag = info.GitTag
	metric.GitHash = info.GitHash
	metric.BuildTime = info.BuildTime
	metric.Pid = int32(os.Getpid())
	metric.NumCPU = runtime.NumCPU()
	metric.SampledAt = toNonNegUint64(time.Now().Unix())

	cur, err := s.takeCPUSample()
	if err != nil {
		logger.Warn("sample probe cpu failed, errmsg: %s", err)
	} else {
		if s.prev == nil {
			uptime, upErr := process.SelfUptime()
			if upErr != nil {
				logger.Warn("sample probe uptime for cpu failed, errmsg: %s", upErr)
			} else {
				metric.CpuUsagePercent = cpuUsageSinceStart(cur.cpuSeconds, uptime)
			}
		} else {
			metric.CpuUsagePercent = cpuUsagePercent(*s.prev, cur)
		}
		s.prev = &cur
	}

	if memInfo, err := s.proc.MemoryInfo(); err != nil {
		logger.Warn("sample probe memory rss failed, errmsg: %s", err)
	} else {
		metric.MemRssMB = memInfo.RSS / 1024 / 1024
	}

	if memPct, err := s.proc.MemoryPercent(); err != nil {
		logger.Warn("sample probe memory percent failed, errmsg: %s", err)
	} else {
		metric.MemUsagePercent = sanitizePercent(float64(memPct))
	}

	if startedAt, err := process.SelfStartedAt(); err != nil {
		logger.Warn("sample probe started_at failed, errmsg: %s", err)
	} else {
		metric.StartedAt = toNonNegUint64(startedAt.Unix())
	}

	if uptime, err := process.SelfUptime(); err != nil {
		logger.Warn("sample probe uptime failed, errmsg: %s", err)
	} else {
		metric.UptimeSeconds = durationToNonNegSeconds(uptime)
		if uptime > 0 {
			metric.Uptime = durafmt.Parse(uptime).LimitFirstN(2).String()
		}
	}

	metric.CpuUsagePercent = sanitizePercent(metric.CpuUsagePercent)
	metric.MemUsagePercent = sanitizePercent(metric.MemUsagePercent)
	s.latest.Store(metric)
}

// run samples every interval until ctx is done or quit is closed.
func (s *sampler) run(ctx context.Context, quit <-chan struct{}, interval time.Duration) {
	s.sampleOnce()
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-quit:
			return
		case <-ticker.C:
			s.sampleOnce()
		}
	}
}

var (
	defaultSampler     *sampler
	defaultSamplerOnce sync.Once
	defaultSamplerErr  error
	runOnce            sync.Once
)

func ensureDefaultSampler() error {
	defaultSamplerOnce.Do(func() {
		defaultSampler, defaultSamplerErr = newSampler()
	})
	return defaultSamplerErr
}

// Run samples the current process on SampleInterval until ctx is done or quit is
// closed. It takes the first sample immediately so Snapshot returns data right
// after startup. Repeated calls are no-ops.
func Run(ctx context.Context, quit <-chan struct{}) {
	runOnce.Do(func() {
		if err := ensureDefaultSampler(); err != nil {
			logger.Warn("init probe self metric sampler failed, errmsg: %s", err)
			return
		}
		defaultSampler.run(ctx, quit, SampleInterval)
	})
}

// Snapshot returns a copy of the latest sampled metric, or nil before the first
// successful sample.
func Snapshot() *haprobe.ProbeMetric {
	if err := ensureDefaultSampler(); err != nil {
		return nil
	}
	return defaultSampler.snapshot()
}
