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

package config

import (
	"context"
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

func cachedRow(age time.Duration) *hamodel.DbmMetadata {
	return &hamodel.DbmMetadata{
		IP:        "127.0.0.1",
		Port:      3306,
		UpdatedAt: time.Now().Add(-age),
	}
}

// TestCacheFallbackReason_WholeMachineIsAllOrNothing pins the rule that one expired row sends
// the entire machine back to DBM. Serving the fresh rows alone would give the probe a
// half-updated view of that host, which is worse than the extra latency of a DBM lookup.
func TestCacheFallbackReason_WholeMachineIsAllOrNothing(t *testing.T) {
	const maxAge = 10 * time.Minute
	now := time.Now()

	cases := []struct {
		name string
		rows []*hamodel.DbmMetadata
		want string
	}{
		{name: "no rows at all", rows: nil, want: fallbackReasonMiss},
		{
			name: "every row fresh",
			rows: []*hamodel.DbmMetadata{cachedRow(time.Minute), cachedRow(2 * time.Minute)},
			want: "",
		},
		{
			name: "one row past the window",
			rows: []*hamodel.DbmMetadata{cachedRow(time.Minute), cachedRow(11 * time.Minute)},
			want: fallbackReasonStale,
		},
		{
			name: "row exactly at the window is still fresh",
			rows: []*hamodel.DbmMetadata{{UpdatedAt: now.Add(-maxAge)}},
			want: "",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := cacheFallbackReason(tc.rows, maxAge, now); got != tc.want {
				t.Errorf("reason: %q, want: %q", got, tc.want)
			}
		})
	}
}

// TestNormalizeProbeMetadata covers the defaults an existing admin config relies on, plus the
// two bounds. Zero means "not configured" here, so an admin.yaml written before this block
// existed must come out with the defaults rather than with checks disabled.
func TestNormalizeProbeMetadata(t *testing.T) {
	cases := []struct {
		name             string
		in               ProbeMetadataConfig
		wantCacheMaxAge  time.Duration
		wantTombstoneAge time.Duration
	}{
		{
			name:             "unset falls back to defaults",
			in:               ProbeMetadataConfig{},
			wantCacheMaxAge:  DefaultProbeMetadataCacheMaxAge,
			wantTombstoneAge: DefaultProbeMetadataTombstoneAge,
		},
		{
			name:             "configured values are kept",
			in:               ProbeMetadataConfig{CacheMaxAge: 5 * time.Minute, TombstoneAge: 2 * time.Hour},
			wantCacheMaxAge:  5 * time.Minute,
			wantTombstoneAge: 2 * time.Hour,
		},
		{
			name:             "cacheMaxAge below the floor is raised",
			in:               ProbeMetadataConfig{CacheMaxAge: time.Second},
			wantCacheMaxAge:  minProbeMetadataCacheMaxAge,
			wantTombstoneAge: DefaultProbeMetadataTombstoneAge,
		},
		{
			name:             "tombstoneAge below cacheMaxAge is raised to it",
			in:               ProbeMetadataConfig{CacheMaxAge: time.Hour, TombstoneAge: time.Minute},
			wantCacheMaxAge:  time.Hour,
			wantTombstoneAge: time.Hour,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := normalizeProbeMetadata(tc.in)
			if got.CacheMaxAge != tc.wantCacheMaxAge {
				t.Errorf("cacheMaxAge: %s, want: %s", got.CacheMaxAge, tc.wantCacheMaxAge)
			}
			if got.TombstoneAge != tc.wantTombstoneAge {
				t.Errorf("tombstoneAge: %s, want: %s", got.TombstoneAge, tc.wantTombstoneAge)
			}
		})
	}
}

// withDbmAPI points the metadata lookup at url for the duration of the test.
func withDbmAPI(t *testing.T, url string, timeout time.Duration) {
	t.Helper()

	saved := Cfg.DbmApis
	t.Cleanup(func() { Cfg.DbmApis = saved })
	Cfg.DbmApis = []DbmApi{{Name: constant.DbmApiNameMetadata, Api: url, Timeout: timeout}}
}

// TestGetMetadataFromDBM_CollapsesConcurrentLookups is the load guard: probes poll on a
// schedule, so a fleet whose cache went stale falls back at the same moment. Those requests
// must reach DBM as one call, not as one per probe.
func TestGetMetadataFromDBM_CollapsesConcurrentLookups(t *testing.T) {
	var calls atomic.Int32
	entered := make(chan struct{})
	release := make(chan struct{})

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		if calls.Add(1) == 1 {
			close(entered)
			<-release
		}
		_, _ = w.Write([]byte(`{"result":true,"data":[{"ip":"127.0.0.1","port":3306}]}`))
	}))
	defer srv.Close()
	withDbmAPI(t, srv.URL, 5*time.Second)

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		if _, err := getMetadataFromDBM(context.Background(), 0, "127.0.0.1"); err != nil {
			t.Errorf("leading lookup failed, errmsg: %s", err)
		}
	}()

	<-entered
	for i := 0; i < 4; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, err := getMetadataFromDBM(context.Background(), 0, "127.0.0.1"); err != nil {
				t.Errorf("joined lookup failed, errmsg: %s", err)
			}
		}()
	}

	// Give the followers time to reach the shared call before letting the leader finish.
	time.Sleep(200 * time.Millisecond)
	close(release)
	wg.Wait()

	if got := calls.Load(); got != 1 {
		t.Fatalf("dbm was called %d times, want 1", got)
	}
}

// TestGetMetadataFromDBM_HonoursContextDeadline is what keeps a hung DBM from becoming a
// permanent block: callers waiting on the shared call would otherwise pile up round after
// round, and the key would never be released.
func TestGetMetadataFromDBM_HonoursContextDeadline(t *testing.T) {
	blocked := make(chan struct{})
	srv := httptest.NewServer(http.HandlerFunc(func(_ http.ResponseWriter, r *http.Request) {
		select {
		case <-blocked:
		case <-r.Context().Done():
		}
	}))
	// Order matters: Close waits for in-flight handlers, so the handlers have to be released
	// first.
	defer srv.Close()
	defer close(blocked)
	withDbmAPI(t, srv.URL, 300*time.Millisecond)

	start := time.Now()
	if _, err := getMetadataFromDBM(context.Background(), 1, "127.0.0.1"); err == nil {
		t.Fatal("expected the lookup to fail once the api timeout passed")
	}
	if elapsed := time.Since(start); elapsed > 5*time.Second {
		t.Fatalf("lookup did not give up promptly, elapsed: %s", elapsed)
	}

	// The key must be usable again: a failed round cannot poison later ones.
	done := make(chan struct{})
	go func() {
		defer close(done)
		next, cancelNext := context.WithTimeout(context.Background(), 300*time.Millisecond)
		defer cancelNext()
		_, _ = getMetadataFromDBM(next, 1, "127.0.0.1")
	}()
	select {
	case <-done:
	case <-time.After(5 * time.Second):
		t.Fatal("the singleflight key stayed blocked after a failure")
	}
}

// TestGetMetadataFromDBM_CancelledCallerDoesNotFailWaiters is why the shared lookup is detached
// from the first caller's context: that probe going away must not abort the round-trip the rest
// of the fleet is already waiting on.
func TestGetMetadataFromDBM_CancelledCallerDoesNotFailWaiters(t *testing.T) {
	entered := make(chan struct{})
	release := make(chan struct{})

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		close(entered)
		<-release
		_, _ = w.Write([]byte(`{"result":true,"data":[{"ip":"127.0.0.1","port":3306}]}`))
	}))
	defer srv.Close()
	withDbmAPI(t, srv.URL, 5*time.Second)

	leaderCtx, cancelLeader := context.WithCancel(context.Background())
	leaderErr := make(chan error, 1)
	go func() {
		_, err := getMetadataFromDBM(leaderCtx, 2, "127.0.0.1")
		leaderErr <- err
	}()

	<-entered
	cancelLeader()

	waiterErr := make(chan error, 1)
	go func() {
		_, err := getMetadataFromDBM(context.Background(), 2, "127.0.0.1")
		waiterErr <- err
	}()

	time.Sleep(100 * time.Millisecond)
	close(release)

	if err := <-leaderErr; err != nil {
		t.Fatalf("cancelled leader still shares the in-flight result, errmsg: %s", err)
	}
	if err := <-waiterErr; err != nil {
		t.Fatalf("waiter failed after the leader cancelled, errmsg: %s", err)
	}
}
