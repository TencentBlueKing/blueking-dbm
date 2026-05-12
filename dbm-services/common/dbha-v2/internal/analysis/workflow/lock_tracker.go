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
	"sync"

	"dbm-services/common/dbha-v2/pkg/logger"
)

// InProcessLockTracker turns the per-biz etcd switch lock into a reentrant lock
// inside a single AM: the first acquirer pays the etcd round-trip; subsequent
// concurrent acquirers for the same bizId share that lock via reference counting,
// so distinct clusters of the same business can be switched in parallel.
// Cross-AM mutual exclusion is unchanged — it is still enforced by etcd.
type InProcessLockTracker struct {
	mu    sync.Mutex
	holds map[int]*heldLock
}

// heldLock is a single etcd lock currently owned by this AM,
// shared among refCnt in-process callers.
type heldLock struct {
	unlock func()
	refCnt int
}

// NewInProcessLockTracker creates an empty tracker.
func NewInProcessLockTracker() *InProcessLockTracker {
	return &InProcessLockTracker{holds: make(map[int]*heldLock)}
}

// acquirerFunc abstracts the underlying lock acquisition so tests can inject
// a fake without depending on a real MetadataReader / etcd client.
type acquirerFunc func(ctx context.Context, bizId int) (unlock func(), err error)

// Acquire acquires the switch lock for bizId and returns a release function.
// It delegates to acquireWith using the real etcd-backed acquirer from reader.
func (t *InProcessLockTracker) Acquire(ctx context.Context, reader *MetadataReader, bizId int) (func(), error) {
	return t.acquireWith(ctx, bizId, func(ctx context.Context, bizId int) (func(), error) {
		_, unlock, err := reader.AcquireSwitchLock(ctx, bizId)
		return unlock, err
	})
}

// acquireWith
// Fast path: bizId already held by this AM → refCnt++.
// Slow path: call etcd outside t.mu so unrelated bizIds are not blocked.
func (t *InProcessLockTracker) acquireWith(ctx context.Context, bizId int, acquirer acquirerFunc) (func(), error) {
	// Fast path: reuse the existing hold.
	t.mu.Lock()
	if h, ok := t.holds[bizId]; ok {
		h.refCnt++
		t.mu.Unlock()
		return t.releaseFunc(bizId), nil
	}
	t.mu.Unlock()

	// Slow path: call etcd outside t.mu so unrelated bizIds are not blocked.
	unlock, err := acquirer(ctx, bizId)
	if err != nil {
		return nil, err
	}

	t.mu.Lock()
	t.holds[bizId] = &heldLock{unlock: unlock, refCnt: 1}
	t.mu.Unlock()
	return t.releaseFunc(bizId), nil
}

// releaseFunc returns a closure that releases one reference for bizId.
func (t *InProcessLockTracker) releaseFunc(bizId int) func() {
	return func() { t.release(bizId) }
}

// release decrements refCnt; on the final reference it removes the entry
// and unlocks etcd outside t.mu to avoid network I/O under the local lock.
func (t *InProcessLockTracker) release(bizId int) {
	t.mu.Lock()
	h, ok := t.holds[bizId]
	if !ok {
		t.mu.Unlock()
		logger.Warn("release called but no lock held, bizId: %d", bizId)
		return
	}

	h.refCnt--
	if h.refCnt > 0 {
		t.mu.Unlock()
		return
	}

	delete(t.holds, bizId)
	unlock := h.unlock
	t.mu.Unlock()

	if unlock != nil {
		unlock()
	}
}

// HeldCount returns the number of bizIds currently held by this AM (diagnostics/tests).
func (t *InProcessLockTracker) HeldCount() int {
	t.mu.Lock()
	defer t.mu.Unlock()
	return len(t.holds)
}
