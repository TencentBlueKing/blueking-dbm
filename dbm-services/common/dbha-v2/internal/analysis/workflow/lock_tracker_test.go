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

package workflow

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

// fakeAcquirer counts acquire / unlock calls and can inject a one-shot failure.
type fakeAcquirer struct {
	mu          sync.Mutex
	callCount   int
	unlockCount int
	failNext    error
}

func (f *fakeAcquirer) acquire(ctx context.Context, bizId int) (func(), error) {
	f.mu.Lock()
	if f.failNext != nil {
		err := f.failNext
		f.failNext = nil
		f.mu.Unlock()
		return nil, err
	}
	f.callCount++
	f.mu.Unlock()

	return func() {
		f.mu.Lock()
		f.unlockCount++
		f.mu.Unlock()
	}, nil
}

func (f *fakeAcquirer) calls() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.callCount
}

func (f *fakeAcquirer) unlocks() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.unlockCount
}

// stubAcquirer simulates etcd mutex semantics: at most one holder per bizId
// at a time. Concurrent acquirers other than the winner receive an error.
// It also counts successes and failures for test assertions.
type stubAcquirer struct {
	mu        sync.Mutex
	held      map[int]bool
	successes int32
	failures  int32
}

func newStubAcquirer() *stubAcquirer {
	return &stubAcquirer{held: make(map[int]bool)}
}

func (s *stubAcquirer) acquire(ctx context.Context, bizId int) (func(), error) {
	s.mu.Lock()
	if s.held[bizId] {
		s.mu.Unlock()
		atomic.AddInt32(&s.failures, 1)
		return nil, errors.New("lock already held")
	}
	s.held[bizId] = true
	atomic.AddInt32(&s.successes, 1)
	s.mu.Unlock()

	return func() {
		s.mu.Lock()
		delete(s.held, bizId)
		s.mu.Unlock()
	}, nil
}

// gateAcquirer blocks until release is called, then returns a no-op unlock.
// Used for deterministic synchronization in tests (replaces time.Sleep).
type gateAcquirer struct {
	gate   chan struct{}
	called chan struct{} // signaled when acquire is entered
}

func newGateAcquirer() *gateAcquirer {
	return &gateAcquirer{
		gate:   make(chan struct{}),
		called: make(chan struct{}),
	}
}

func (g *gateAcquirer) acquire(ctx context.Context, bizId int) (func(), error) {
	close(g.called) // notify: acquire has been entered
	<-g.gate        // block until external release
	return func() {}, nil
}

func (g *gateAcquirer) release() {
	close(g.gate)
}

func (g *gateAcquirer) entered() <-chan struct{} {
	return g.called
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// TestLockTracker_FastPathReentrant: a second Acquire while the first still
// holds the lock takes the fast path (no extra acquirer call, refCnt=2),
// and the underlying lock is only released on the final reference.
func TestLockTracker_FastPathReentrant(t *testing.T) {
	tracker := NewInProcessLockTracker()
	fa := &fakeAcquirer{}

	release1, err := tracker.acquireWith(context.Background(), 1001, fa.acquire)
	if err != nil {
		t.Fatalf("first acquire failed: %s", err)
	}

	release2, err := tracker.acquireWith(context.Background(), 1001, fa.acquire)
	if err != nil {
		t.Fatalf("second acquire failed: %s", err)
	}

	if got := fa.calls(); got != 1 {
		t.Fatalf("expected acquirer called once, got: %d", got)
	}
	if got := tracker.HeldCount(); got != 1 {
		t.Fatalf("expected 1 held, got: %d", got)
	}

	release1()
	if got := fa.unlocks(); got != 0 {
		t.Fatalf("unlock should not be called yet, got: %d", got)
	}
	if got := tracker.HeldCount(); got != 1 {
		t.Fatalf("hold should still be present after partial release, got: %d", got)
	}

	release2()
	if got := fa.unlocks(); got != 1 {
		t.Fatalf("unlock should be called once after final release, got: %d", got)
	}
	if got := tracker.HeldCount(); got != 0 {
		t.Fatalf("hold should be removed after final release, got: %d", got)
	}
}

// TestLockTracker_AcquirerError: an acquirer error propagates and leaves no hold;
// a subsequent acquire still works.
func TestLockTracker_AcquirerError(t *testing.T) {
	tracker := NewInProcessLockTracker()
	fa := &fakeAcquirer{failNext: errors.New("lock held by another AM")}

	_, err := tracker.acquireWith(context.Background(), 2002, fa.acquire)
	if err == nil {
		t.Fatal("expected error from acquirer, got nil")
	}
	if got := tracker.HeldCount(); got != 0 {
		t.Fatalf("expected 0 held after acquire failure, got: %d", got)
	}

	release, err := tracker.acquireWith(context.Background(), 2002, fa.acquire)
	if err != nil {
		t.Fatalf("subsequent acquire failed: %s", err)
	}
	release()
}

// TestLockTracker_ReleaseAndReacquire: after fully releasing, a new Acquire
// goes through the slow path again (acquirer is invoked).
func TestLockTracker_ReleaseAndReacquire(t *testing.T) {
	tracker := NewInProcessLockTracker()
	fa := &fakeAcquirer{}

	release1, err := tracker.acquireWith(context.Background(), 3003, fa.acquire)
	if err != nil {
		t.Fatalf("first acquire failed: %s", err)
	}
	release1()

	release2, err := tracker.acquireWith(context.Background(), 3003, fa.acquire)
	if err != nil {
		t.Fatalf("second acquire failed: %s", err)
	}
	release2()

	if got := fa.calls(); got != 2 {
		t.Fatalf("expected 2 underlying acquire calls, got: %d", got)
	}
	if got := fa.unlocks(); got != 2 {
		t.Fatalf("expected 2 underlying unlock calls, got: %d", got)
	}
}

// TestLockTracker_ConcurrentSlowPath_OnlyOneWinner: with etcd-like mutex
// semantics, concurrent first-time acquires for the same bizId result in
// exactly one winner; the rest get an error and leave no hold.
// Winners hold their locks until after wg.Wait so that late goroutines
// cannot re-acquire the stub lock after an early winner releases.
func TestLockTracker_ConcurrentSlowPath_OnlyOneWinner(t *testing.T) {
	tracker := NewInProcessLockTracker()
	sa := newStubAcquirer()

	const n = 20
	startBarrier := make(chan struct{})
	var successes, failures int32
	releaseCh := make(chan func(), n)

	var wg sync.WaitGroup
	wg.Add(n)
	for i := 0; i < n; i++ {
		go func() {
			defer wg.Done()
			<-startBarrier
			rel, err := tracker.acquireWith(context.Background(), 4004, sa.acquire)
			if err != nil {
				atomic.AddInt32(&failures, 1)
				return
			}
			atomic.AddInt32(&successes, 1)
			releaseCh <- rel
		}()
	}

	close(startBarrier)
	wg.Wait()
	close(releaseCh)

	// Collect and release all successful holds.
	var holds []func()
	for rel := range releaseCh {
		holds = append(holds, rel)
	}

	// Exactly one goroutine must have succeeded at the underlying acquirer.
	if got := atomic.LoadInt32(&sa.successes); got != 1 {
		t.Fatalf("expected exactly 1 successful underlying acquire, got: %d", got)
	}
	// The remaining goroutines either took the fast path (tracker-level success)
	// or lost the slow-path race (etcd mutex error). Both are valid outcomes.
	// Verify the total is consistent: tracker successes + etcd failures == n.
	trackerSuccesses := int32(len(holds))
	etcdFailures := atomic.LoadInt32(&sa.failures)
	if trackerSuccesses+etcdFailures != n {
		t.Fatalf("expected tracker successes (%d) + etcd failures (%d) == %d",
			trackerSuccesses, etcdFailures, n)
	}
	if got := tracker.HeldCount(); got != 1 {
		t.Fatalf("expected exactly 1 hold, got: %d", got)
	}

	// Release all holds.
	for _, rel := range holds {
		rel()
	}
	if got := tracker.HeldCount(); got != 0 {
		t.Fatalf("expected 0 holds after all releases, got: %d", got)
	}
}

// TestLockTracker_FastPathAfterSlowPathSuccess: once a slow-path acquire
// succeeds and registers a hold, subsequent acquires for the same bizId
// take the fast path (refCnt bumps) without calling the underlying acquirer.
func TestLockTracker_FastPathAfterSlowPathSuccess(t *testing.T) {
	tracker := NewInProcessLockTracker()
	fa := &fakeAcquirer{}

	// First acquire goes slow path.
	release1, err := tracker.acquireWith(context.Background(), 4004, fa.acquire)
	if err != nil {
		t.Fatalf("first acquire failed: %s", err)
	}

	// Subsequent acquires should all be fast path.
	const extra = 5
	releases := make([]func(), extra)
	for i := 0; i < extra; i++ {
		rel, err := tracker.acquireWith(context.Background(), 4004, fa.acquire)
		if err != nil {
			t.Fatalf("fast-path acquire %d failed: %s", i, err)
		}
		releases[i] = rel
	}

	// Underlying acquirer should only have been called once.
	if got := fa.calls(); got != 1 {
		t.Fatalf("expected 1 underlying acquire call, got: %d", got)
	}
	// Still a single hold entry.
	if got := tracker.HeldCount(); got != 1 {
		t.Fatalf("expected 1 hold, got: %d", got)
	}

	// Partial releases should not unlock yet.
	for _, rel := range releases {
		rel()
	}
	if got := fa.unlocks(); got != 0 {
		t.Fatalf("unlock should not be called after partial releases, got: %d", got)
	}

	// Final release triggers the underlying unlock.
	release1()
	if got := fa.unlocks(); got != 1 {
		t.Fatalf("expected 1 underlying unlock after final release, got: %d", got)
	}
	if got := tracker.HeldCount(); got != 0 {
		t.Fatalf("expected 0 holds after final release, got: %d", got)
	}
}

// TestLockTracker_DifferentBizDoNotBlockEachOther: a slow acquire on one bizId
// must not block acquires on other bizIds. Uses gateAcquirer for deterministic
// synchronization instead of relying on time.Sleep.
func TestLockTracker_DifferentBizDoNotBlockEachOther(t *testing.T) {
	tracker := NewInProcessLockTracker()
	ga := newGateAcquirer()

	// Slow acquire on bizId=5005: blocks until ga.release() is called.
	go func() {
		rel, err := tracker.acquireWith(context.Background(), 5005, ga.acquire)
		if err != nil {
			t.Errorf("slow acquire returned error: %s", err)
			return
		}
		rel()
	}()

	// Wait until the slow acquirer has actually entered acquireWith's slow path.
	<-ga.entered()

	// Fast acquire on bizId=5006 should complete without waiting.
	doneCh := make(chan struct{})
	go func() {
		rel, err := tracker.acquireWith(context.Background(), 5006,
			func(ctx context.Context, bizId int) (func(), error) {
				return func() {}, nil
			})
		if err != nil {
			t.Errorf("fast acquire returned error: %s", err)
			return
		}
		rel()
		close(doneCh)
	}()

	select {
	case <-doneCh:
		// ok: fast biz completed while slow biz was still blocking
	case <-time.After(time.Second):
		t.Fatal("fast biz acquire was blocked by slow biz acquire")
	}

	// Unblock the slow acquirer so the goroutine can finish.
	ga.release()
}

// TestLockTracker_ReleaseUnknownBizIsSafe: releasing a bizId that is not held
// must not panic.
func TestLockTracker_ReleaseUnknownBizIsSafe(t *testing.T) {
	tracker := NewInProcessLockTracker()
	tracker.release(9999)
}

// TestLockTracker_DoubleRelease: calling the same release function more than
// once must not panic or cause the underlying unlock to be invoked multiple
// times. The second call hits the "no lock held" branch and logs a warning.
func TestLockTracker_DoubleRelease(t *testing.T) {
	tracker := NewInProcessLockTracker()
	fa := &fakeAcquirer{}

	release, err := tracker.acquireWith(context.Background(), 6001, fa.acquire)
	if err != nil {
		t.Fatalf("acquire failed: %s", err)
	}

	// First release: refCnt 1→0, underlying unlock called.
	release()
	if got := fa.unlocks(); got != 1 {
		t.Fatalf("expected 1 unlock after first release, got: %d", got)
	}
	if got := tracker.HeldCount(); got != 0 {
		t.Fatalf("expected 0 holds after first release, got: %d", got)
	}

	// Second release: hold already removed, should not panic or double-unlock.
	release()
	if got := fa.unlocks(); got != 1 {
		t.Fatalf("expected still 1 unlock after double release, got: %d", got)
	}
	if got := tracker.HeldCount(); got != 0 {
		t.Fatalf("expected 0 holds after double release, got: %d", got)
	}
}

// TestLockTracker_ConcurrentReacquireAfterRelease: after the last reference
// for a bizId is released (hold removed), multiple goroutines concurrently
// acquiring the same bizId must go through slow path again, and with etcd
// mutex semantics only one wins at the underlying level. The rest get errors
// but the tracker should remain consistent.
func TestLockTracker_ConcurrentReacquireAfterRelease(t *testing.T) {
	tracker := NewInProcessLockTracker()
	sa := newStubAcquirer()

	// Phase 1: acquire and release once to establish the "was held, now free" state.
	rel, err := tracker.acquireWith(context.Background(), 7001, sa.acquire)
	if err != nil {
		t.Fatalf("initial acquire failed: %s", err)
	}
	rel()
	if got := tracker.HeldCount(); got != 0 {
		t.Fatalf("expected 0 holds after initial release, got: %d", got)
	}

	// Phase 2: concurrent re-acquire after release.
	const n = 20
	startBarrier := make(chan struct{})
	releaseCh := make(chan func(), n)

	var wg sync.WaitGroup
	wg.Add(n)
	for i := 0; i < n; i++ {
		go func() {
			defer wg.Done()
			<-startBarrier
			r, err := tracker.acquireWith(context.Background(), 7001, sa.acquire)
			if err != nil {
				return
			}
			releaseCh <- r
		}()
	}

	close(startBarrier)
	wg.Wait()
	close(releaseCh)

	// Collect successful holds.
	var holds []func()
	for r := range releaseCh {
		holds = append(holds, r)
	}

	// Exactly one goroutine won the underlying etcd lock.
	if got := atomic.LoadInt32(&sa.successes); got != 2 {
		// 1 from phase 1 + 1 from phase 2
		t.Fatalf("expected 2 total successful underlying acquires (1 per phase), got: %d", got)
	}

	// tracker successes + etcd failures == n (for phase 2 only).
	trackerSuccesses := int32(len(holds))
	// Phase 2 failures = total failures (phase 1 had none).
	etcdFailures := atomic.LoadInt32(&sa.failures)
	if trackerSuccesses+etcdFailures != n {
		t.Fatalf("expected tracker successes (%d) + etcd failures (%d) == %d",
			trackerSuccesses, etcdFailures, n)
	}

	// Release all holds.
	for _, r := range holds {
		r()
	}
	if got := tracker.HeldCount(); got != 0 {
		t.Fatalf("expected 0 holds after all releases, got: %d", got)
	}
}
