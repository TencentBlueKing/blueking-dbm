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

package base

import (
	"context"
	"sync"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Host metrics are machine-wide: one process-level sampler takes the snapshots
// and every collector reads the latest one instead of sampling the machine per
// instance. The cadence comes from collect.hostMetricInterval, and the sampler
// owns no default so that a single place decides it.

// hostMetricLabel labels recovered panics of the host metric sampler.
const hostMetricLabel = "HostMetric"

// hostMetricLatest holds the newest machine-wide host metric snapshot.
var hostMetricLatest atomic.Pointer[haprobe.HostMetric]

// hostMetricReset carries a new sample interval to the running sampler.
var hostMetricReset = make(chan time.Duration, 1)

var hostMetricOnce sync.Once

// StartHostMetric launches the process-wide host metric sampler.
//
// ctx must be the process context: the sampler outlives harvester generations so
// a reload does not discard the baseline. Repeated calls are no-ops.
func StartHostMetric(ctx context.Context, interval time.Duration) {
	hostMetricOnce.Do(func() {
		// Take the first sample synchronously: the first collection round starts
		// as soon as the plugins are up, so the snapshot must already be there or
		// every instance of that round falls back to sampling the machine itself.
		sampleHostMetric()
		// Log the interval that is actually in effect: a config value that never
		// reaches the sampler (or is overwritten later) is otherwise invisible.
		logger.Info("host metric sampler started, interval: %s", interval)

		safe.Go(func() {
			ticker := time.NewTicker(interval)
			defer ticker.Stop()

			for {
				select {
				case <-ctx.Done():
					return
				case next := <-hostMetricReset:
					// A reload may change the cadence: keep the sampler and its
					// current snapshot, only retune the ticker.
					if next > 0 && next != interval {
						interval = next
						ticker.Reset(interval)
						logger.Info("host metric sample interval updated, interval: %s", interval)
					}
				case <-ticker.C:
					sampleHostMetric()
				}
			}
		}, safe.WithLabel(hostMetricLabel))
	})
}

// SetHostMetricInterval retunes the sample interval of the already running
// sampler. The sampler is never rebuilt, so the current snapshot and any
// accumulated state survive a reload. It is a no-op before the sampler starts
// (StartHostMetric then owns the initial interval) and for a non-positive
// interval.
func SetHostMetricInterval(interval time.Duration) {
	if interval <= 0 {
		return
	}

	select {
	case hostMetricReset <- interval:
	default:
	}
}

// sampleHostMetric collects one host metric and stores it as a brand new object.
// Storing a new object (rather than mutating a shared one) is what makes
// concurrent reads safe without a lock.
func sampleHostMetric() {
	var c Collector
	hs := &haprobe.HostMetric{}

	if err := c.SetCpuStatus(hs); err != nil {
		logger.Warn("host metric: failed to update CPU status, errmsg: %s", err)
	}
	if err := c.SetNetStatus(hs); err != nil {
		logger.Warn("host metric: failed to update net status, errmsg: %s", err)
	}
	if err := c.SetMemoryStatus(hs); err != nil {
		logger.Warn("host metric: failed to update memory status, errmsg: %s", err)
	}
	if err := c.SetDiskStatus(hs); err != nil {
		logger.Warn("host metric: failed to update disk status, errmsg: %s", err)
	}

	hostMetricLatest.Store(hs)
}

// HostMetricSnapshot returns a copy of the newest host metric, or nil before the
// first sample finishes.
//
// NetIPs is a slice, so it is copied: callers must not share the backing array.
func HostMetricSnapshot() *haprobe.HostMetric {
	m := hostMetricLatest.Load()
	if m == nil {
		return nil
	}

	cpy := *m
	if m.NetIPs != nil {
		cpy.NetIPs = append([]string(nil), m.NetIPs...)
	}
	return &cpy
}
