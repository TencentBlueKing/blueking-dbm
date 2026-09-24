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

package kafka

import (
	"context"
	"errors"
	"io"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"

	"github.com/IBM/sarama"
)

type fakeConsumerGroup struct {
	consumeFn    func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error
	closeCount   atomic.Int32
	consumeCalls atomic.Int32
	errors       chan error
	closeOnce    sync.Once
}

func newFakeConsumerGroup(
	consumeFn func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error,
) *fakeConsumerGroup {
	return &fakeConsumerGroup{
		consumeFn: consumeFn,
		errors:    make(chan error),
	}
}

func (f *fakeConsumerGroup) Consume(
	ctx context.Context,
	topics []string,
	handler sarama.ConsumerGroupHandler,
) error {
	f.consumeCalls.Add(1)
	if f.consumeFn == nil {
		return nil
	}
	return f.consumeFn(ctx, topics, handler)
}

func (f *fakeConsumerGroup) Errors() <-chan error {
	return f.errors
}

func (f *fakeConsumerGroup) Close() error {
	f.closeCount.Add(1)
	f.closeOnce.Do(func() {
		close(f.errors)
	})
	return nil
}

func (f *fakeConsumerGroup) Pause(map[string][]int32)  {}
func (f *fakeConsumerGroup) Resume(map[string][]int32) {}
func (f *fakeConsumerGroup) PauseAll()                 {}
func (f *fakeConsumerGroup) ResumeAll()                {}

func newTestConsumer(t *testing.T, newGroup newConsumerGroupFunc) *consumer {
	t.Helper()
	return &consumer{
		endpoints:  []string{"127.0.0.1:9092"},
		topics:     []string{"test-topic"},
		cliCfg:     sarama.NewConfig(),
		quit:       make(chan struct{}),
		newGroup:   newGroup,
		minBackoff: 5 * time.Millisecond,
		maxBackoff: 40 * time.Millisecond,
	}
}

func waitHarvestDone(t *testing.T, c *consumer, timeout time.Duration) {
	t.Helper()
	done := make(chan struct{})
	go func() {
		c.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-time.After(timeout):
		t.Fatal("harvest loop did not stop in time")
	}
}

func TestHarvestRetriesOnIOTimeout(t *testing.T) {
	var call int32
	group := newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
		n := atomic.AddInt32(&call, 1)
		if n <= 2 {
			return io.ErrUnexpectedEOF
		}
		<-ctx.Done()
		return ctx.Err()
	})

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		return group, nil
	})

	ctx, cancel := context.WithCancel(context.Background())
	if err := c.Harvest(ctx, nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}

	deadline := time.Now().Add(2 * time.Second)
	for atomic.LoadInt32(&call) < 3 && time.Now().Before(deadline) {
		time.Sleep(5 * time.Millisecond)
	}
	if atomic.LoadInt32(&call) < 3 {
		t.Fatalf("expected at least 3 Consume calls, got: %d", atomic.LoadInt32(&call))
	}

	cancel()
	waitHarvestDone(t, c, time.Second)
}

func TestHarvestImmediateNilBackoff(t *testing.T) {
	var (
		mu       sync.Mutex
		times    []time.Time
		call     int32
		stopOnce sync.Once
		stopCh   = make(chan struct{})
	)

	group := newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
		n := atomic.AddInt32(&call, 1)
		mu.Lock()
		times = append(times, time.Now())
		mu.Unlock()
		if n >= 3 {
			stopOnce.Do(func() { close(stopCh) })
			<-ctx.Done()
			return ctx.Err()
		}
		return nil
	})

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		return group, nil
	})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := c.Harvest(ctx, nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}

	select {
	case <-stopCh:
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for quick-nil Consume calls")
	}

	mu.Lock()
	defer mu.Unlock()
	if len(times) < 3 {
		t.Fatalf("expected at least 3 timestamps, got: %d", len(times))
	}
	gap1 := times[1].Sub(times[0])
	gap2 := times[2].Sub(times[1])
	if gap1 < c.minBackoff/2 {
		t.Fatalf("first backoff too small: %s", gap1)
	}
	if gap2 < gap1 {
		t.Fatalf("expected backoff to grow, gap1: %s, gap2: %s", gap1, gap2)
	}

	cancel()
	waitHarvestDone(t, c, time.Second)
}

func TestHarvestLongLivedErrorResetsBackoff(t *testing.T) {
	var (
		call     int32
		waits    []time.Duration
		mu       sync.Mutex
		prevEnd  time.Time
		stopOnce sync.Once
		stopCh   = make(chan struct{})
	)

	c := newTestConsumer(t, nil)
	c.minBackoff = 20 * time.Millisecond
	c.maxBackoff = 80 * time.Millisecond
	c.newGroup = func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		return newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
			n := atomic.AddInt32(&call, 1)
			mu.Lock()
			if !prevEnd.IsZero() {
				waits = append(waits, time.Since(prevEnd))
			}
			mu.Unlock()

			if n == 1 {
				time.Sleep(c.minBackoff)
				mu.Lock()
				prevEnd = time.Now()
				mu.Unlock()
				return errors.New("flush failed")
			}
			stopOnce.Do(func() { close(stopCh) })
			<-ctx.Done()
			return ctx.Err()
		}), nil
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := c.Harvest(ctx, nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}

	select {
	case <-stopCh:
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for second Consume")
	}

	mu.Lock()
	defer mu.Unlock()
	if len(waits) < 1 {
		t.Fatal("expected at least one wait sample")
	}
	if waits[0] > c.minBackoff*3 {
		t.Fatalf("expected backoff reset to min, wait: %s", waits[0])
	}

	cancel()
	waitHarvestDone(t, c, time.Second)
}

func TestHarvestStopsWhenQuitAlreadyClosed(t *testing.T) {
	group := newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
		return sarama.ErrClosedConsumerGroup
	})

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		return group, nil
	})
	c.closeOnce.Do(func() { close(c.quit) })

	if err := c.Harvest(context.Background(), nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}
	waitHarvestDone(t, c, time.Second)
}

func TestHarvestRebuildsOnErrClosedConsumerGroupWhileRunning(t *testing.T) {
	var (
		newGroupCalls atomic.Int32
		consumeCalls  atomic.Int32
		stopOnce      sync.Once
		stopCh        = make(chan struct{})
	)

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		newGroupCalls.Add(1)
		return newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
			n := consumeCalls.Add(1)
			if n == 1 {
				return sarama.ErrClosedConsumerGroup
			}
			stopOnce.Do(func() { close(stopCh) })
			<-ctx.Done()
			return ctx.Err()
		}), nil
	})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := c.Harvest(ctx, nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}

	select {
	case <-stopCh:
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for rebuild")
	}

	if newGroupCalls.Load() < 2 {
		t.Fatalf("expected newGroup called at least twice, got: %d", newGroupCalls.Load())
	}

	cancel()
	waitHarvestDone(t, c, time.Second)
}

func TestEnsureGroupRetriesCreate(t *testing.T) {
	var (
		newGroupCalls atomic.Int32
		consumeCalls  atomic.Int32
		stopOnce      sync.Once
		stopCh        = make(chan struct{})
	)

	group := newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
		consumeCalls.Add(1)
		stopOnce.Do(func() { close(stopCh) })
		<-ctx.Done()
		return ctx.Err()
	})

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		n := newGroupCalls.Add(1)
		if n <= 2 {
			return nil, errors.New("broker unavailable")
		}
		return group, nil
	})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := c.Harvest(ctx, nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}

	select {
	case <-stopCh:
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for successful create")
	}

	if consumeCalls.Load() < 1 {
		t.Fatal("expected Consume to be called after create succeeds")
	}

	cancel()
	waitHarvestDone(t, c, time.Second)
}

func TestHarvestRecoversFromNewGroupPanic(t *testing.T) {
	var (
		newGroupCalls atomic.Int32
		stopOnce      sync.Once
		stopCh        = make(chan struct{})
	)

	group := newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
		stopOnce.Do(func() { close(stopCh) })
		<-ctx.Done()
		return ctx.Err()
	})

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		n := newGroupCalls.Add(1)
		if n == 1 {
			panic("create panic")
		}
		return group, nil
	})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := c.Harvest(ctx, nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}

	select {
	case <-stopCh:
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting after newGroup panic")
	}

	cancel()
	waitHarvestDone(t, c, time.Second)
}

func TestHarvestRecoversFromConsumePanic(t *testing.T) {
	var (
		newGroupCalls atomic.Int32
		consumeCalls  atomic.Int32
		stopOnce      sync.Once
		stopCh        = make(chan struct{})
	)

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		newGroupCalls.Add(1)
		return newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
			n := consumeCalls.Add(1)
			if n == 1 {
				panic("consume panic")
			}
			stopOnce.Do(func() { close(stopCh) })
			<-ctx.Done()
			return ctx.Err()
		}), nil
	})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := c.Harvest(ctx, nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}

	select {
	case <-stopCh:
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting after Consume panic")
	}

	if newGroupCalls.Load() < 2 {
		t.Fatalf("expected rebuild after panic, newGroup calls: %d", newGroupCalls.Load())
	}

	cancel()
	waitHarvestDone(t, c, time.Second)
}

func TestHarvestRebuildsEveryFiveFailures(t *testing.T) {
	var (
		newGroupCalls atomic.Int32
		consumeCalls  atomic.Int32
		stopOnce      sync.Once
		stopCh        = make(chan struct{})
	)

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		newGroupCalls.Add(1)
		return newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
			n := consumeCalls.Add(1)
			if n <= 10 {
				return errors.New("temporary failure")
			}
			stopOnce.Do(func() { close(stopCh) })
			<-ctx.Done()
			return ctx.Err()
		}), nil
	})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	if err := c.Harvest(ctx, nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}

	select {
	case <-stopCh:
	case <-time.After(5 * time.Second):
		t.Fatal("timed out waiting for 10 failures")
	}

	if got := newGroupCalls.Load(); got != 3 {
		t.Fatalf("expected newGroup called 3 times (1 create + 2 rebuilds), got: %d", got)
	}

	cancel()
	waitHarvestDone(t, c, time.Second)
}

func TestEnsureGroupSkippedAfterQuit(t *testing.T) {
	var newGroupCalls atomic.Int32
	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		newGroupCalls.Add(1)
		return newFakeConsumerGroup(nil), nil
	})
	c.closeOnce.Do(func() { close(c.quit) })

	if _, err := c.ensureGroup(); !errors.Is(err, errConsumerStopping) {
		t.Fatalf("expected errConsumerStopping, got: %v", err)
	}
	if newGroupCalls.Load() != 0 {
		t.Fatalf("expected no newGroup call after quit, got: %d", newGroupCalls.Load())
	}
}

func TestCloseDuringNewGroup(t *testing.T) {
	started := make(chan struct{})
	release := make(chan struct{})
	var closed atomic.Int32

	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		close(started)
		<-release
		g := newFakeConsumerGroup(nil)
		return &closeTrackingGroup{fakeConsumerGroup: g, closed: &closed}, nil
	})

	errCh := make(chan error, 1)
	go func() {
		_, err := c.ensureGroup()
		errCh <- err
	}()

	select {
	case <-started:
	case <-time.After(time.Second):
		t.Fatal("newGroup did not start")
	}

	doneClose := make(chan struct{})
	go func() {
		c.Close()
		close(doneClose)
	}()

	select {
	case <-doneClose:
	case <-time.After(time.Second):
		t.Fatal("Close blocked on lock while newGroup was running")
	}

	close(release)

	select {
	case err := <-errCh:
		if !errors.Is(err, errConsumerStopping) {
			t.Fatalf("expected errConsumerStopping, got: %v", err)
		}
	case <-time.After(time.Second):
		t.Fatal("ensureGroup did not return")
	}

	deadline := time.Now().Add(time.Second)
	for closed.Load() < 1 && time.Now().Before(deadline) {
		time.Sleep(5 * time.Millisecond)
	}
	if closed.Load() < 1 {
		t.Fatal("expected newly created group to be closed after quit")
	}
}

type closeTrackingGroup struct {
	*fakeConsumerGroup
	closed *atomic.Int32
}

func (c *closeTrackingGroup) Close() error {
	c.closed.Add(1)
	return c.fakeConsumerGroup.Close()
}

func TestCloseDuringBackoff(t *testing.T) {
	group := newFakeConsumerGroup(func(ctx context.Context, topics []string, handler sarama.ConsumerGroupHandler) error {
		return errors.New("i/o timeout")
	})
	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		return group, nil
	})
	c.minBackoff = 500 * time.Millisecond
	c.maxBackoff = 500 * time.Millisecond

	if err := c.Harvest(context.Background(), nil); err != nil {
		t.Fatalf("Harvest failed, errmsg: %s", err)
	}
	time.Sleep(20 * time.Millisecond)
	c.Close()
	waitHarvestDone(t, c, time.Second)
}

func TestAdjustGroupTimeouts(t *testing.T) {
	cases := []struct {
		name        string
		readTimeout time.Duration
	}{
		{name: "100s", readTimeout: 100 * time.Second},
		{name: "61s", readTimeout: 61 * time.Second},
		{name: "30s", readTimeout: 30 * time.Second},
		{name: "10s", readTimeout: 10 * time.Second},
		{name: "1s", readTimeout: 1 * time.Second},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cfg := sarama.NewConfig()
			cfg.Net.ReadTimeout = tc.readTimeout
			adjustGroupTimeouts(cfg)

			if cfg.Net.ReadTimeout <= cfg.Consumer.Group.Rebalance.Timeout {
				t.Fatalf(
					"ReadTimeout must be > Rebalance.Timeout, read: %s, rebalance: %s",
					cfg.Net.ReadTimeout, cfg.Consumer.Group.Rebalance.Timeout,
				)
			}
			if cfg.Consumer.Group.Rebalance.Timeout < cfg.Consumer.Group.Session.Timeout {
				t.Fatalf(
					"Rebalance.Timeout must be >= Session.Timeout, rebalance: %s, session: %s",
					cfg.Consumer.Group.Rebalance.Timeout, cfg.Consumer.Group.Session.Timeout,
				)
			}
		})
	}
}

func TestNewRejectsEmptyTopics(t *testing.T) {
	_, err := New(config.SourceConfig{
		Endpoints: "127.0.0.1:9092",
		Topics:    nil,
	})
	if err == nil {
		t.Fatal("expected error for empty topics")
	}
	var ge *gerrors.Error
	if !errors.As(err, &ge) || !ge.HasCode(gerrors.InvalidConfiguration) {
		t.Fatalf("expected InvalidConfiguration, got: %v", err)
	}
}

func TestRebuildAndCloseRace(t *testing.T) {
	group := newFakeConsumerGroup(nil)
	c := newTestConsumer(t, func(addrs []string, groupID string, config *sarama.Config) (sarama.ConsumerGroup, error) {
		return group, nil
	})
	c.group = group

	var wg sync.WaitGroup
	wg.Add(2)
	go func() {
		defer wg.Done()
		c.rebuildGroup(group, 5)
	}()
	go func() {
		defer wg.Done()
		c.Close()
	}()
	wg.Wait()

	if group.closeCount.Load() < 1 {
		t.Fatal("expected group.Close to be called at least once")
	}
}
