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
	"errors"
	"net"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"

	clientv3 "go.etcd.io/etcd/client/v3"
)

const readTestTimeout = 300 * time.Millisecond

// unusedLoopbackEndpoint returns a 127.0.0.1 address with nothing listening on it.
func unusedLoopbackEndpoint(t *testing.T) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed, errmsg: %s", err)
	}
	addr := ln.Addr().String()
	_ = ln.Close()

	return addr
}

func newCountingDiscovery(t *testing.T) (*Discovery, *atomic.Int32) {
	t.Helper()
	endpoint := unusedLoopbackEndpoint(t)
	calls := &atomic.Int32{}
	d := &Discovery{
		quit: make(chan struct{}),
		createEtcdClient: func() (*clientv3.Client, error) {
			calls.Add(1)
			return clientv3.New(clientv3.Config{Endpoints: []string{endpoint}})
		},
	}

	return d, calls
}

func assertEtcdFailure(t *testing.T, err error) {
	t.Helper()
	var gerr *gerrors.Error
	if !errors.As(err, &gerr) || gerr.Code() != gerrors.EtcdFailure.Int() {
		t.Fatalf("err: %v, want EtcdFailure", err)
	}
}

func TestDiscoveryGetWithPrefixWithoutWatch(t *testing.T) {
	d, calls := newCountingDiscovery(t)
	defer d.Close()

	ctx, cancel := context.WithTimeout(context.Background(), readTestTimeout)
	defer cancel()

	_, err := d.GetWithPrefix(ctx, HaServerSelfPrefix(HaServerRoleAdmin))
	assertEtcdFailure(t, err)
	if got := calls.Load(); got != 1 {
		t.Fatalf("L06 factory calls: %d, want: 1", got)
	}
}

func TestDiscoveryReadAfterClose(t *testing.T) {
	d, calls := newCountingDiscovery(t)
	d.Close()

	_, err := d.Get(context.Background(), "/dbha/registry/admin/self/a1")
	if !errors.Is(err, ErrDiscoveryClosed) {
		t.Fatalf("L07 Get err: %v", err)
	}
	assertEtcdFailure(t, err)

	_, err = d.GetWithPrefix(context.Background(), HaServerSelfPrefix(HaServerRoleAdmin))
	if !errors.Is(err, ErrDiscoveryClosed) {
		t.Fatalf("L07 GetWithPrefix err: %v", err)
	}

	if got := calls.Load(); got != 0 {
		t.Fatalf("L07 factory calls: %d, want: 0", got)
	}
}

func TestDiscoveryConcurrentReadAndClose(t *testing.T) {
	d, calls := newCountingDiscovery(t)

	const readers = 16
	errs := make(chan error, readers)
	var wg sync.WaitGroup
	for i := 0; i < readers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			ctx, cancel := context.WithTimeout(context.Background(), readTestTimeout)
			defer cancel()
			_, err := d.GetWithPrefix(ctx, HaServerSelfPrefix(HaServerRoleAnalysis))
			errs <- err
		}()
	}

	time.Sleep(10 * time.Millisecond)
	d.Close()
	wg.Wait()
	close(errs)

	for err := range errs {
		assertEtcdFailure(t, err)
	}

	if got := calls.Load(); got > 1 {
		t.Fatalf("L08 factory calls: %d, want at most: 1", got)
	}
}

func TestDiscoveryWatchThenRead(t *testing.T) {
	d, calls := newCountingDiscovery(t)
	defer d.Close()

	ctx, cancel := context.WithTimeout(context.Background(), readTestTimeout)
	defer cancel()

	if _, err := d.WatchWithPrefix(ctx, HaServerSelfPrefix(HaServerRoleAnalysis)); err != nil {
		t.Fatalf("L09 watch failed, errmsg: %s", err)
	}

	_, err := d.GetWithPrefix(ctx, HaServerSelfPrefix(HaServerRoleAnalysis))
	assertEtcdFailure(t, err)
	if got := calls.Load(); got != 1 {
		t.Fatalf("L09 factory calls: %d, want: 1", got)
	}
}

const lockTestTimeout = time.Second

// waitDone reports whether done is closed within timeout.
func waitDone(done <-chan struct{}, timeout time.Duration) bool {
	select {
	case <-done:
		return true
	case <-time.After(timeout):
		return false
	}
}

// goDone runs fn in a goroutine and returns a channel closed when fn returns.
func goDone(fn func()) <-chan struct{} {
	done := make(chan struct{})
	go func() {
		defer close(done)
		fn()
	}()

	return done
}

// assertWatchClosed drains ch and fails unless it is closed within timeout.
func assertWatchClosed(t *testing.T, ch <-chan *WatchEvent, timeout time.Duration) {
	t.Helper()
	deadline := time.After(timeout)
	for {
		select {
		case _, ok := <-ch:
			if !ok {
				return
			}
		case <-deadline:
			t.Fatalf("watch channel not closed within: %s", timeout)
		}
	}
}

func newClosedLoopbackClient(t *testing.T) *clientv3.Client {
	t.Helper()
	cli, err := clientv3.New(clientv3.Config{Endpoints: []string{unusedLoopbackEndpoint(t)}})
	if err != nil {
		t.Fatalf("create client failed, errmsg: %s", err)
	}
	_ = cli.Close()

	return cli
}

func TestWatchClosedChannelExits(t *testing.T) {
	d, _ := newCountingDiscovery(t)
	d.client = newClosedLoopbackClient(t)
	defer d.Close()

	watchChan, err := d.WatchWithPrefix(context.Background(), HaServerSelfPrefix(HaServerRoleAnalysis))
	if err != nil {
		t.Fatalf("watch failed, errmsg: %s", err)
	}

	assertWatchClosed(t, watchChan, lockTestTimeout)
}

func TestPendingWatchDoesNotBlockReadOrClose(t *testing.T) {
	d, _ := newCountingDiscovery(t)
	prefix := HaServerSelfPrefix(HaServerRoleAnalysis)

	watchDone := goDone(func() {
		_, _ = d.WatchWithPrefix(context.Background(), prefix)
	})
	time.Sleep(100 * time.Millisecond)

	var readErr error
	readDone := goDone(func() {
		ctx, cancel := context.WithTimeout(context.Background(), readTestTimeout)
		defer cancel()
		_, readErr = d.GetWithPrefix(ctx, prefix)
	})
	if !waitDone(readDone, lockTestTimeout) {
		t.Fatalf("read blocked by pending watch over: %s", lockTestTimeout)
	}
	assertEtcdFailure(t, readErr)

	if !waitDone(goDone(d.Close), lockTestTimeout) {
		t.Fatalf("close blocked by pending watch over: %s", lockTestTimeout)
	}

	if !waitDone(watchDone, lockTestTimeout) {
		t.Fatalf("pending watch not returned after close within: %s", lockTestTimeout)
	}
}

func newLoopbackClient(t *testing.T) *clientv3.Client {
	t.Helper()
	cli, err := clientv3.New(clientv3.Config{Endpoints: []string{unusedLoopbackEndpoint(t)}})
	if err != nil {
		t.Fatalf("create client failed, errmsg: %s", err)
	}

	return cli
}

func TestDiscoveryReadReleasesLock(t *testing.T) {
	d, _ := newCountingDiscovery(t)
	defer d.Close()

	ctx, cancel := context.WithTimeout(context.Background(), readTestTimeout)
	defer cancel()

	_, err := d.Get(ctx, "/dbha/registry/admin/self/a1")
	assertEtcdFailure(t, err)
	_, err = d.GetWithPrefix(ctx, HaServerSelfPrefix(HaServerRoleAdmin))
	assertEtcdFailure(t, err)

	locked := goDone(func() {
		d.cliMu.Lock()
		d.cliMu.Unlock()
	})
	if !waitDone(locked, lockTestTimeout) {
		t.Fatalf("cliMu still held after failed reads over: %s", lockTestTimeout)
	}
}

func TestWithReadClientPanicReleasesLock(t *testing.T) {
	d, _ := newCountingDiscovery(t)

	func() {
		defer func() {
			if r := recover(); r == nil {
				t.Fatal("expected panic from fn")
			}
		}()
		_ = d.withReadClient(func(*clientv3.Client) error {
			panic("fn panic")
		})
	}()

	if !waitDone(goDone(d.Close), lockTestTimeout) {
		t.Fatalf("close blocked after fn panic over: %s", lockTestTimeout)
	}
}

func TestWithReadClientAfterClose(t *testing.T) {
	d, calls := newCountingDiscovery(t)
	d.Close()

	called := false
	err := d.withReadClient(func(*clientv3.Client) error {
		called = true
		return nil
	})
	if !errors.Is(err, ErrDiscoveryClosed) {
		t.Fatalf("err: %v, want: ErrDiscoveryClosed", err)
	}
	if called {
		t.Fatal("fn called after close")
	}
	if got := calls.Load(); got != 0 {
		t.Fatalf("factory calls: %d, want: 0", got)
	}
}

func TestDropClientOnlyCurrent(t *testing.T) {
	d, _ := newCountingDiscovery(t)
	defer d.Close()

	old := newLoopbackClient(t)
	defer old.Close()
	cur := newLoopbackClient(t)
	d.client = cur

	d.dropClient(old)
	if d.client != cur {
		t.Fatal("dropClient with a stale client changed the current client")
	}

	d.dropClient(cur)
	if d.client != nil {
		t.Fatal("dropClient with the current client did not clear it")
	}
	d.dropClient(cur)
}

func TestWatchAfterClose(t *testing.T) {
	d, calls := newCountingDiscovery(t)
	d.Close()

	_, err := d.WatchWithPrefix(context.Background(), HaServerSelfPrefix(HaServerRoleAnalysis))
	if !errors.Is(err, ErrDiscoveryClosed) {
		t.Fatalf("err: %v, want: ErrDiscoveryClosed", err)
	}
	if got := calls.Load(); got != 0 {
		t.Fatalf("factory calls: %d, want: 0", got)
	}
}

func TestWatchExitsWhenClientClosed(t *testing.T) {
	d, _ := newCountingDiscovery(t)
	defer d.Close()
	cli := newLoopbackClient(t)
	d.client = cli

	var watchChan <-chan *WatchEvent
	var watchErr error
	watchDone := goDone(func() {
		watchChan, watchErr = d.WatchWithPrefix(context.Background(), HaServerSelfPrefix(HaServerRoleAnalysis))
	})
	time.Sleep(100 * time.Millisecond)
	_ = cli.Close()

	if !waitDone(watchDone, lockTestTimeout) {
		t.Fatalf("watch not returned after client closed within: %s", lockTestTimeout)
	}
	if watchErr != nil {
		t.Fatalf("watch failed, errmsg: %s", watchErr)
	}
	assertWatchClosed(t, watchChan, lockTestTimeout)
}

func TestConcurrentWatchAndClose(t *testing.T) {
	d, _ := newCountingDiscovery(t)
	prefix := HaServerSelfPrefix(HaServerRoleAnalysis)

	const watchers = 16
	chans := make(chan (<-chan *WatchEvent), watchers)
	errs := make(chan error, watchers)
	var wg sync.WaitGroup
	for i := 0; i < watchers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			ch, err := d.WatchWithPrefix(context.Background(), prefix)
			if err != nil {
				errs <- err
				return
			}
			chans <- ch
		}()
	}

	time.Sleep(10 * time.Millisecond)
	if !waitDone(goDone(d.Close), lockTestTimeout) {
		t.Fatalf("close blocked by concurrent watchers over: %s", lockTestTimeout)
	}
	if !waitDone(goDone(wg.Wait), lockTestTimeout) {
		t.Fatalf("watchers not returned after close within: %s", lockTestTimeout)
	}
	close(chans)
	close(errs)

	for err := range errs {
		if !errors.Is(err, ErrDiscoveryClosed) {
			t.Fatalf("err: %v, want: ErrDiscoveryClosed", err)
		}
	}
	for ch := range chans {
		assertWatchClosed(t, ch, lockTestTimeout)
	}
}
