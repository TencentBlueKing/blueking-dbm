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
	"sync"
	"testing"
	"time"
)

// waitFor polls cond until it holds or the deadline expires.
func waitFor(t *testing.T, cond func() bool) {
	t.Helper()

	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if cond() {
			return
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatal("condition was not met before the deadline")
}

// collectKey builds a job key the way the harvesters do.
func collectKey(port int) string {
	return fmt.Sprintf("127.0.0.1:%d", port)
}

func TestCollectPool_LimitsConcurrentJobs(t *testing.T) {
	const workers = 4
	const jobCount = 32

	p := newCollectPool()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	p.SetWorkers(ctx, workers)

	var mu sync.Mutex
	inFlight := 0
	peak := 0
	release := make(chan struct{})
	finished := make(chan struct{}, jobCount)

	for i := 0; i < jobCount; i++ {
		job := CollectJob{
			Key: collectKey(30000 + i),
			Run: func() {
				mu.Lock()
				inFlight++
				if inFlight > peak {
					peak = inFlight
				}
				mu.Unlock()

				<-release

				mu.Lock()
				inFlight--
				mu.Unlock()
				finished <- struct{}{}
			},
		}
		if !p.Submit(job) {
			t.Fatalf("submit job failed, index: %d", i)
		}
	}

	waitFor(t, func() bool {
		mu.Lock()
		defer mu.Unlock()
		return inFlight == workers
	})

	close(release)
	for i := 0; i < jobCount; i++ {
		select {
		case <-finished:
		case <-time.After(5 * time.Second):
			t.Fatalf("job did not finish, remaining: %d", jobCount-i)
		}
	}

	mu.Lock()
	got := peak
	mu.Unlock()
	if got > workers {
		t.Fatalf("concurrent jobs exceeded the worker count, peak: %d, workers: %d", got, workers)
	}
}

func TestCollectPool_DedupSameInstance(t *testing.T) {
	p := newCollectPool()
	block := make(chan struct{})

	if !p.Submit(CollectJob{Key: collectKey(30000), Run: func() { <-block }}) {
		t.Fatal("first submit should succeed")
	}
	if p.Submit(CollectJob{Key: collectKey(30000), Run: func() {}}) {
		t.Fatal("duplicate submit of the same instance should be skipped")
	}
	if p.Pending() != 1 {
		t.Fatalf("pending = %d, want 1", p.Pending())
	}
	close(block)
}

func TestCollectPool_DedupKeepsDifferentInstances(t *testing.T) {
	p := newCollectPool()

	if !p.Submit(CollectJob{Key: collectKey(30000), Run: func() {}}) {
		t.Fatal("first instance should be accepted")
	}
	if !p.Submit(CollectJob{Key: collectKey(30001), Run: func() {}}) {
		t.Fatal("a different instance must not be deduped")
	}
	if p.Pending() != 2 {
		t.Fatalf("pending = %d, want 2", p.Pending())
	}
}

func TestCollectPool_ResubmitAfterJobDone(t *testing.T) {
	p := newCollectPool()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	p.SetWorkers(ctx, 1)

	started := make(chan struct{})
	if !p.Submit(CollectJob{Key: collectKey(30000), Run: func() { close(started) }}) {
		t.Fatal("first submit should succeed")
	}
	<-started

	waitFor(t, func() bool { return p.Pending() == 0 })

	if !p.Submit(CollectJob{Key: collectKey(30000), Run: func() {}}) {
		t.Fatal("resubmit after the job finished should succeed")
	}
}

func TestCollectPool_SubmitDoesNotBlockWhenQueueFull(t *testing.T) {
	p := newCollectPool()

	// No worker is started, so every accepted job stays in the queue.
	for i := 0; i < collectJobQueueCap; i++ {
		if !p.Submit(CollectJob{Key: collectKey(30000 + i), Run: func() {}}) {
			t.Fatalf("queue should accept the job, index: %d", i)
		}
	}

	if p.Submit(CollectJob{Key: collectKey(39999), Run: func() {}}) {
		t.Fatal("submit should be skipped when the queue is full")
	}
	if p.Pending() != collectJobQueueCap {
		t.Fatalf("pending = %d, want %d", p.Pending(), collectJobQueueCap)
	}
}

func TestCollectPool_SetWorkersResizes(t *testing.T) {
	p := newCollectPool()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	p.SetWorkers(ctx, 2)
	if p.Workers() != 2 {
		t.Fatalf("workers = %d, want 2", p.Workers())
	}

	p.SetWorkers(ctx, 5)
	if p.Workers() != 5 {
		t.Fatalf("workers = %d, want 5", p.Workers())
	}

	p.SetWorkers(ctx, 1)
	if p.Workers() != 1 {
		t.Fatalf("workers = %d, want 1", p.Workers())
	}

	p.SetWorkers(ctx, 0)
	if p.Workers() != 1 {
		t.Fatalf("an invalid size must keep the current one, workers = %d", p.Workers())
	}
}

// TestCollectPool_WorkersOutliveGenerationContext guards the two-context split:
// a resize during a reload must not rebind the workers to the generation context.
func TestCollectPool_WorkersOutliveGenerationContext(t *testing.T) {
	p := newCollectPool()
	procCtx, procCancel := context.WithCancel(context.Background())
	defer procCancel()

	p.SetWorkers(procCtx, 1)

	genCtx, genCancel := context.WithCancel(procCtx)
	genCancel()
	p.SetWorkers(genCtx, 3)

	ran := make(chan struct{}, 3)
	for i := 0; i < 3; i++ {
		if !p.Submit(CollectJob{Key: collectKey(30000 + i), Run: func() { ran <- struct{}{} }}) {
			t.Fatalf("submit job failed, index: %d", i)
		}
	}

	for i := 0; i < 3; i++ {
		select {
		case <-ran:
		case <-time.After(5 * time.Second):
			t.Fatalf("worker exited with the generation context, remaining: %d", 3-i)
		}
	}
}

func TestCollectPool_WorkersExitOnProcessContextDone(t *testing.T) {
	p := newCollectPool()
	ctx, cancel := context.WithCancel(context.Background())
	p.SetWorkers(ctx, 3)
	cancel()

	exited := make(chan struct{})
	go func() {
		p.Wait()
		close(exited)
	}()

	select {
	case <-exited:
	case <-time.After(5 * time.Second):
		t.Fatal("workers did not exit after the process context was done")
	}
}

func TestCollectPool_RecoversJobPanic(t *testing.T) {
	p := newCollectPool()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	p.SetWorkers(ctx, 1)

	done := make(chan struct{})
	p.Submit(CollectJob{Key: collectKey(30000), Run: func() { panic("boom") }})
	p.Submit(CollectJob{Key: collectKey(30001), Run: func() { close(done) }})

	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("the pool stopped after a job panicked")
	}
	waitFor(t, func() bool { return p.Pending() == 0 })
}
