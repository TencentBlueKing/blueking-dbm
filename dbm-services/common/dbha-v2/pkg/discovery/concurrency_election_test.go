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
)

// mockElection implements discovery.ConcurrencyElection for testing
type mockElection struct {
	campaignErr error
	done        chan struct{}
	closed      bool
	mu          sync.Mutex
}

func newMockElection(campaignErr error) *mockElection {
	return &mockElection{
		campaignErr: campaignErr,
		done:        make(chan struct{}),
	}
}

func (m *mockElection) Campaign(ctx context.Context) error {
	return m.campaignErr
}

func (m *mockElection) Close() {
	m.mu.Lock()
	defer m.mu.Unlock()
	if !m.closed {
		close(m.done)
		m.closed = true
	}
}

func (m *mockElection) Done() <-chan struct{} {
	return m.done
}

// Verify mockElection implements the interface
var _ ConcurrencyElection = (*mockElection)(nil)

func TestConcurrencyElectionInterface(t *testing.T) {
	t.Run("campaign_success", func(t *testing.T) {
		mock := newMockElection(nil)
		var election ConcurrencyElection = mock

		err := election.Campaign(context.Background())
		if err != nil {
			t.Fatalf("Campaign() unexpected error: %v", err)
		}
		t.Logf("Campaign() succeeded")
	})

	t.Run("campaign_failure", func(t *testing.T) {
		mock := newMockElection(context.DeadlineExceeded)
		var election ConcurrencyElection = mock

		err := election.Campaign(context.Background())
		if err == nil {
			t.Fatal("Campaign() expected error, got nil")
		}
		t.Logf("Campaign() returned expected error: %v", err)
	})

	t.Run("done_channel", func(t *testing.T) {
		mock := newMockElection(nil)
		var election ConcurrencyElection = mock

		done := election.Done()
		if done == nil {
			t.Fatal("Done() returned nil channel")
		}

		select {
		case <-done:
			t.Fatal("Done() channel should not be closed yet")
		default:
			t.Logf("Done() channel is open")
		}
	})

	t.Run("close_idempotent", func(t *testing.T) {
		mock := newMockElection(nil)
		var election ConcurrencyElection = mock

		election.Close()
		election.Close() // should not panic

		select {
		case <-election.Done():
			t.Logf("Done() channel closed after Close()")
		default:
			t.Fatal("Done() channel should be closed after Close()")
		}
	})
}
