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
