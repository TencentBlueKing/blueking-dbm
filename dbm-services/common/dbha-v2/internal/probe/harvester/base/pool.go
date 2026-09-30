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
	"fmt"
	"sort"
	"sync"
	"sync/atomic"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/safe"
)

const (
	// collectJobQueueCap is the capacity of the pending job queue. Dedup keeps
	// queued jobs at or below the instance count, so this is only a safety net:
	// a full queue means the pool is far behind.
	collectJobQueueCap = 2048

	// collectJobLabel labels recovered panics of collection jobs.
	collectJobLabel = "Collect"

	// collectHealthLabel labels recovered panics of the pool health check.
	collectHealthLabel = "CollectHealth"

	// collectFullWarnInterval throttles the "queue full" warning: a sustained
	// backlog would otherwise repeat it on every single submission.
	collectFullWarnInterval = int64(30 * time.Second)

	// collectStuckThreshold is how long a single job may run before the worker is
	// considered stuck. Healthy collection finishes in well under a second, so
	// anything near this is a hang rather than merely a slow instance.
	collectStuckThreshold = 30 * time.Second

	// collectHealthInterval is how often the pool inspects its own progress.
	collectHealthInterval = 60 * time.Second

	// collectStuckRatio is the share (percent) of workers that must be stuck
	// before the pool reports itself blocked. A full stall is not required: once
	// most workers hang the pool can no longer keep up, and waiting for all of
	// them hides the problem for far too long.
	collectStuckRatio = 70
)

// StuckJob describes a job that has been running for unusually long. Key carries
// dbType:ip:port:harvestType, so it names the exact instance and group.
type StuckJob struct {
	Key     string
	Running time.Duration
}

// CollectJob is one collection task. Key identifies the instance being probed
// and is used for dedup; Run performs the collection.
type CollectJob struct {
	Key string
	Run func()
}

// JobKey builds the dedup key of one collection job. It carries the harvest
// type so different harvest types of the same ip:port never block each other.
func JobKey(dbType, ip string, port int, harvestType string) string {
	return fmt.Sprintf("%s:%s:%d:%s", dbType, ip, port, harvestType)
}

// CollectPool bounds the number of concurrent collection goroutines with a fixed
// set of long-lived workers.
//
// The pool is process-wide: workers outlive individual harvester generations so
// that a configuration reload resizes it instead of rebuilding it. Consequently
// the worker context is the process context, while every job closure captures
// its own generation context and abandons itself once that context is done.
type CollectPool struct {
	mu       sync.Mutex
	jobs     chan CollectJob
	pending  map[string]struct{}
	inflight map[string]int64 // key -> start unix nano
	quits    []chan struct{}
	workers  int
	wg       sync.WaitGroup
	procCtx  context.Context

	droppedFull  atomic.Uint64 // jobs dropped because the queue was full
	lastFullWarn atomic.Int64  // unix nano of the last "queue full" warning

	healthOnce sync.Once
	lastQueued int // queued depth at the previous health check
}

// defaultPool is the process-wide pool shared by every harvester plugin.
var defaultPool = newCollectPool()

// DefaultPool returns the process-wide collection pool.
func DefaultPool() *CollectPool {
	return defaultPool
}

// newCollectPool builds an empty pool with no workers.
func newCollectPool() *CollectPool {
	return &CollectPool{
		jobs:     make(chan CollectJob, collectJobQueueCap),
		pending:  make(map[string]struct{}),
		inflight: make(map[string]int64),
	}
}

// SetWorkers resizes the pool to n workers.
//
// ctx is the process-level context; it is adopted on the first call only, so
// later resizes during a reload never shorten the lifetime of running workers.
// Growing starts new workers immediately. Shrinking closes the surplus quit
// channels, which lets those workers exit only after their current job finishes.
func (p *CollectPool) SetWorkers(ctx context.Context, n int) {
	p.mu.Lock()
	defer p.mu.Unlock()

	if n <= 0 {
		logger.Warn("invalid collect worker count, keep the current one, configured: %d, current: %d",
			n, p.workers)
		return
	}

	if p.procCtx == nil {
		p.procCtx = ctx
	}

	if n == p.workers {
		return
	}

	// The self-check shares the process lifetime of the workers it reports on.
	p.startHealthCheck(p.procCtx)

	if n > p.workers {
		p.grow(n)
	} else {
		p.shrink(n)
	}
	p.workers = n
	logger.Info("collect pool resized, workers: %d", n)
}

// grow starts workers until the pool owns n of them. Callers must hold p.mu.
func (p *CollectPool) grow(n int) {
	for i := p.workers; i < n; i++ {
		quit := make(chan struct{})
		p.quits = append(p.quits, quit)
		p.wg.Add(1)
		go p.worker(p.procCtx, quit)
	}
}

// shrink stops surplus workers. Callers must hold p.mu.
func (p *CollectPool) shrink(n int) {
	for i := n; i < p.workers; i++ {
		close(p.quits[i])
		p.quits[i] = nil
	}
	p.quits = p.quits[:n]
}

// Submit enqueues one job unless the same key is already pending.
//
// It never blocks: it reports false when the job is skipped, either because the
// instance is still queued or in progress (dedup) or because the queue is full.
func (p *CollectPool) Submit(job CollectJob) bool {
	if job.Key == "" {
		return false
	}

	p.mu.Lock()
	if _, ok := p.pending[job.Key]; ok {
		p.mu.Unlock()
		return false
	}
	p.pending[job.Key] = struct{}{}
	p.mu.Unlock()

	select {
	case p.jobs <- job:
		return true
	default:
		p.markDone(job.Key)
		p.warnQueueFull(job.Key)
		return false
	}
}

// worker runs jobs until the process context is done or it is quit by a shrink.
func (p *CollectPool) worker(ctx context.Context, quit <-chan struct{}) {
	defer p.wg.Done()

	for {
		select {
		case <-ctx.Done():
			return

		case <-quit:
			return

		case job, ok := <-p.jobs:
			if !ok {
				return
			}
			p.beginJob(job.Key)
			safe.Run(job.Run, safe.WithLabel(collectJobLabel))
			p.endJob(job.Key)
			p.markDone(job.Key)
		}
	}
}

// markDone releases the dedup slot so the instance can be submitted again.
func (p *CollectPool) markDone(key string) {
	p.mu.Lock()
	delete(p.pending, key)
	p.mu.Unlock()
}

// beginJob records that a worker started running this key.
func (p *CollectPool) beginJob(key string) {
	p.mu.Lock()
	p.inflight[key] = time.Now().UnixNano()
	p.mu.Unlock()
}

// endJob records that the worker finished running this key.
func (p *CollectPool) endJob(key string) {
	p.mu.Lock()
	delete(p.inflight, key)
	p.mu.Unlock()
}

// Queued returns the number of jobs waiting for a free worker.
func (p *CollectPool) Queued() int {
	return len(p.jobs)
}

// Inflight returns the number of jobs currently being executed by workers.
func (p *CollectPool) Inflight() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	return len(p.inflight)
}

// StuckJobs returns the jobs that have been running for at least min, longest
// first. Their keys name the exact instance and harvest group, which is what
// makes a hang attributable instead of merely visible.
func (p *CollectPool) StuckJobs(min time.Duration) []StuckJob {
	p.mu.Lock()
	defer p.mu.Unlock()

	now := time.Now().UnixNano()
	out := make([]StuckJob, 0, len(p.inflight))
	for key, start := range p.inflight {
		if running := time.Duration(now - start); running >= min {
			out = append(out, StuckJob{Key: key, Running: running})
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Running > out[j].Running })
	return out
}

// warnQueueFull records a job dropped because the queue was full, and reports it.
//
// A dedup skip is normal (the instance's previous collection is still running) and
// stays silent; a full queue instead means the pool is far behind, which is worth a
// warning. The warning is throttled so a sustained backlog cannot flood the log.
func (p *CollectPool) warnQueueFull(key string) {
	dropped := p.droppedFull.Add(1)

	now := time.Now().UnixNano()
	last := p.lastFullWarn.Load()
	if last != 0 && now-last < collectFullWarnInterval {
		return
	}
	if !p.lastFullWarn.CompareAndSwap(last, now) {
		return
	}
	logger.Warn("[collect-pool] OVERFLOW: queue is full (cap %d), dropping jobs — %d dropped in total, last key=%s | "+
		"CAUSE: the backlog exceeded the queue; those instances are skipped this round. | "+
		"ACTION: the periodic BLOCKED / SATURATED check reports why the backlog built up",
		collectJobQueueCap, dropped, key)
}

// startHealthCheck starts the periodic self-check on the process context.
func (p *CollectPool) startHealthCheck(ctx context.Context) {
	if ctx == nil {
		return
	}
	p.healthOnce.Do(func() {
		safe.Go(func() {
			ticker := time.NewTicker(collectHealthInterval)
			defer ticker.Stop()
			for {
				select {
				case <-ctx.Done():
					return
				case <-ticker.C:
					p.logHealth()
				}
			}
		}, safe.WithLabel(collectHealthLabel))
	})
}

// logHealth reports the pool state and, more importantly, states what the numbers
// mean and what to do about them: the point is that an operator can read the cause
// and the action directly instead of guessing from raw counters.
//
// It stays silent while the pool keeps up, so a healthy probe logs nothing.
func (p *CollectPool) logHealth() {
	p.mu.Lock()
	workers := p.workers
	queued := len(p.jobs)
	inflight := len(p.inflight)
	pending := len(p.pending)
	p.mu.Unlock()

	stuck := p.StuckJobs(collectStuckThreshold)

	grew := queued - p.lastQueued
	p.lastQueued = queued

	switch {
	case workers > 0 && len(stuck)*100 >= workers*collectStuckRatio:
		// Most workers are occupied by jobs that do not finish.
		logger.Warn("[collect-pool] BLOCKED: %d/%d workers stuck (%d%% threshold), oldest job running %s (key=%s); "+
			"queued=%d, inflight=%d, pending=%d | "+
			"CAUSE: jobs are not finishing. If the report channel is full this is report-side blocking "+
			"(check the receiver / Post); otherwise instances are hanging (check DB reachability or host IO). | "+
			"ACTION: raising collectTaskGoroutines will NOT help while workers are stuck",
			len(stuck), workers, collectStuckRatio, stuck[0].Running, stuck[0].Key, queued, inflight, pending)

	case workers > 0 && inflight >= workers && queued > workers:
		// Every worker is busy and a backlog is piling up.
		logger.Warn("[collect-pool] SATURATED: all %d workers busy, queued=%d (%+d since last check), inflight=%d,"+
			" stuck=%d | CAUSE: collection cannot keep up with the configured interval — too many instances, too short "+
			"an interval, instances that became slower, or instances hanging until their timeout. | "+
			"ACTION: raise collect.collectTaskGoroutines (now %d) or lengthen the interval",
			workers, queued, grew, inflight, len(stuck), workers)
	}
}

// Workers returns the current worker count.
func (p *CollectPool) Workers() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.workers
}

// Pending returns the number of instances queued or currently being collected.
func (p *CollectPool) Pending() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	return len(p.pending)
}

// Wait blocks until every worker has exited. It is only meaningful after the
// process context is done, which is what tests rely on.
func (p *CollectPool) Wait() {
	p.wg.Wait()
}
