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

package discovery

import (
	"context"
	"sync"
	"testing"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// mockMutex implements discovery.ConcurrencyMutex for testing
type mockMutex struct {
	locked     bool
	tryLockErr error
	unlockErr  error
	mu         sync.Mutex
	closed     bool
}

func newMockMutex() *mockMutex {
	return &mockMutex{}
}

func (m *mockMutex) TryLock(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.tryLockErr != nil {
		return m.tryLockErr
	}

	if m.locked {
		return gerrors.New(gerrors.Failure, "already locked")
	}

	m.locked = true
	return nil
}

func (m *mockMutex) Unlock(ctx context.Context) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.unlockErr != nil {
		return m.unlockErr
	}

	if !m.locked {
		return gerrors.New(gerrors.Failure, "not locked")
	}

	m.locked = false
	return nil
}

func (m *mockMutex) Close() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.closed = true
}

// Verify mockMutex implements the interface
var _ ConcurrencyMutex = (*mockMutex)(nil)

func TestConcurrencyMutexInterface(t *testing.T) {
	t.Run("trylock_success", func(t *testing.T) {
		mock := newMockMutex()
		var mutex ConcurrencyMutex = mock

		err := mutex.TryLock(context.Background())
		if err != nil {
			t.Fatalf("TryLock() unexpected error: %v", err)
		}
		t.Logf("TryLock() succeeded")
	})

	t.Run("unlock_success", func(t *testing.T) {
		mock := newMockMutex()
		var mutex ConcurrencyMutex = mock

		_ = mutex.TryLock(context.Background())
		err := mutex.Unlock(context.Background())
		if err != nil {
			t.Fatalf("Unlock() unexpected error: %v", err)
		}
		t.Logf("Unlock() succeeded")
	})

	t.Run("double_lock_fails", func(t *testing.T) {
		mock := newMockMutex()
		var mutex ConcurrencyMutex = mock

		_ = mutex.TryLock(context.Background())
		err := mutex.TryLock(context.Background())
		if err == nil {
			t.Fatal("TryLock() expected error on double lock, got nil")
		}
		t.Logf("TryLock() returned expected error: %v", err)
	})

	t.Run("unlock_without_lock_fails", func(t *testing.T) {
		mock := newMockMutex()
		var mutex ConcurrencyMutex = mock

		err := mutex.Unlock(context.Background())
		if err == nil {
			t.Fatal("Unlock() expected error without lock, got nil")
		}
		t.Logf("Unlock() returned expected error: %v", err)
	})

	t.Run("concurrent_access", func(t *testing.T) {
		mock := newMockMutex()
		var mutex ConcurrencyMutex = mock

		var wg sync.WaitGroup
		successCount := 0
		var countMu sync.Mutex

		for i := 0; i < 10; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				if err := mutex.TryLock(context.Background()); err == nil {
					countMu.Lock()
					successCount++
					countMu.Unlock()
					_ = mutex.Unlock(context.Background())
				}
			}()
		}

		wg.Wait()
		if successCount == 0 {
			t.Fatal("concurrent TryLock: at least one goroutine should succeed")
		}
		t.Logf("concurrent TryLock: %d succeeded", successCount)
	})
}
