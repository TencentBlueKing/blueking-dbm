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

package redispasswd

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// resetService restores the shared singleton, so tests must not run in parallel.
func resetService(t *testing.T) *service {
	t.Helper()

	s := instance()
	s.cache.Clear()

	s.mu.Lock()
	s.cfg = QueryConfig{}
	s.resolved = false
	s.loader = nil
	s.mu.Unlock()

	return s
}

// fakePasswdServer stands in for the DBM password service and records what it was asked.
type fakePasswdServer struct {
	*httptest.Server

	mu       sync.Mutex
	requests []queryPasswdRequest

	// respond builds the reply; see defaultRespond.
	respond func(req queryPasswdRequest) queryPasswdResponse
}

// newFakePasswdServer starts a fake service that is closed with the test.
func newFakePasswdServer(t *testing.T) *fakePasswdServer {
	t.Helper()

	f := &fakePasswdServer{respond: defaultRespond}
	f.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		req := queryPasswdRequest{}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		f.mu.Lock()
		f.requests = append(f.requests, req)
		respond := f.respond
		f.mu.Unlock()

		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(respond(req)); err != nil {
			t.Errorf("failed to encode the fake response: %s", err)
		}
	}))
	t.Cleanup(f.Close)

	return f
}

// recorded returns a copy of the requests received so far.
func (f *fakePasswdServer) recorded() []queryPasswdRequest {
	f.mu.Lock()
	defer f.mu.Unlock()

	out := make([]queryPasswdRequest, len(f.requests))
	copy(out, f.requests)
	return out
}

// requestCount returns how many requests the fake service has answered.
func (f *fakePasswdServer) requestCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()

	return len(f.requests)
}

// setRespond swaps the reply builder.
func (f *fakePasswdServer) setRespond(fn func(req queryPasswdRequest) queryPasswdResponse) {
	f.mu.Lock()
	defer f.mu.Unlock()

	f.respond = fn
}

// defaultRespond returns one item per requested instance and user pair.
func defaultRespond(req queryPasswdRequest) queryPasswdResponse {
	rsp := queryPasswdResponse{}
	for _, inst := range req.Instances {
		for _, user := range req.Users {
			rsp.Data.Items = append(rsp.Data.Items, passwdItem{
				IP:        inst.IP,
				Port:      inst.Port,
				BkCloudID: inst.BkCloudID,
				UserName:  user.UserName,
				Component: user.Component,
				Password:  encodePasswd(plainPasswd(inst.IP, user.Component)),
			})
		}
	}
	rsp.Data.Count = len(rsp.Data.Items)

	return rsp
}

// plainPasswd is the password the fake service holds for one instance and component.
func plainPasswd(ip, component string) string {
	return fmt.Sprintf("passwd-%s-%s", ip, component)
}

// encodePasswd encodes a password the way the service does.
func encodePasswd(passwd string) string {
	return base64.StdEncoding.EncodeToString([]byte(passwd))
}

// configure points the singleton at the fake server without going through a loader.
func configure(t *testing.T, f *fakePasswdServer) {
	t.Helper()

	ApplyQueryConfig(QueryConfig{API: f.URL, Token: "token", Timeout: 5 * time.Second})
}

func TestGetDbInstPasswd_NoConfigLoaderFails(t *testing.T) {
	resetService(t)

	if _, err := GetDbInstPasswd(0, 1, haprobe.DbmMetadataMachineTypeTendisCache); err == nil {
		t.Fatal("expected an error when no config loader is registered")
	}
}

func TestGetDbInstPasswd_EmptyApiFails(t *testing.T) {
	resetService(t)
	RegisterConfigLoader(func() QueryConfig { return QueryConfig{Token: "token"} })

	if _, err := GetDbInstPasswd(0, 1, haprobe.DbmMetadataMachineTypeTendisCache); err == nil {
		t.Fatal("expected an error when the query api is empty")
	}
}

func TestGetDbInstPasswd_LoaderRunsLazilyAndOnce(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)

	calls := 0
	RegisterConfigLoader(func() QueryConfig {
		calls++
		return QueryConfig{API: f.URL, Token: "token", Timeout: 5 * time.Second}
	})

	if calls != 0 {
		t.Fatalf("the loader ran at registration time, calls: %d", calls)
	}

	if _, err := GetDbInstPasswd(0, 1, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if _, err := GetDbInstPasswd(0, 2, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	if calls != 1 {
		t.Fatalf("the loader ran more than once, calls: %d", calls)
	}
}

func TestGetDbInstPasswd_CachesAcrossCalls(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	first, err := GetDbInstPasswd(0, 1001, haprobe.DbmMetadataMachineTypeTendisCache)
	if err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if want := plainPasswd("1001", componentRedis); first != want {
		t.Fatalf("unexpected password, got: %s, want: %s", first, want)
	}

	second, err := GetDbInstPasswd(0, 1001, haprobe.DbmMetadataMachineTypeTendisCache)
	if err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if second != first {
		t.Fatalf("cached password differs, got: %s, want: %s", second, first)
	}

	if got := f.requestCount(); got != 1 {
		t.Fatalf("the second lookup was not served from cache, requests: %d", got)
	}
}

func TestGetDbInstPasswd_CachesEveryReturnedComponent(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	// One query returns both components, so the storage lookup caches the proxy one.
	if _, err := GetDbInstPasswd(0, 2002, haprobe.DbmMetadataMachineTypeTendisPlus); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	proxyPasswd, err := GetDbInstPasswd(0, 2002, haprobe.DbmMetadataMachineTypeTwemProxy)
	if err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if want := plainPasswd("2002", componentRedisProxy); proxyPasswd != want {
		t.Fatalf("unexpected proxy password, got: %s, want: %s", proxyPasswd, want)
	}

	if got := f.requestCount(); got != 1 {
		t.Fatalf("the proxy lookup issued its own query, requests: %d", got)
	}
}

func TestGetDbInstPasswd_MachineTypeSelectsComponent(t *testing.T) {
	cases := []struct {
		machineType haprobe.DbmMetadataMachineType
		component   string
	}{
		{haprobe.DbmMetadataMachineTypeTendisCache, componentRedis},
		{haprobe.DbmMetadataMachineTypeTendisPlus, componentRedis},
		{haprobe.DbmMetadataMachineTypeTendisSSD, componentRedis},
		{haprobe.DbmMetadataMachineTypeTwemProxy, componentRedisProxy},
		{haprobe.DbmMetadataMachineTypePredixy, componentRedisProxy},
	}

	for _, c := range cases {
		t.Run(string(c.machineType), func(t *testing.T) {
			resetService(t)
			f := newFakePasswdServer(t)
			configure(t, f)

			passwd, err := GetDbInstPasswd(0, 7, c.machineType)
			if err != nil {
				t.Fatalf("unexpected error: %s", err)
			}
			if want := plainPasswd("7", c.component); passwd != want {
				t.Fatalf("unexpected password, got: %s, want: %s", passwd, want)
			}
		})
	}
}

func TestGetDbInstPasswd_UnknownMachineTypeHasNoPassword(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	// An unmapped machine type resolves to a component the query never covers.
	if _, err := GetDbInstPasswd(0, 8, haprobe.DbmMetadataMachineType("unknown")); err == nil {
		t.Fatal("expected an error for a machine type without a queried component")
	}
}

func TestGetDbInstPasswd_RequestShape(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	if _, err := GetDbInstPasswd(42, 1234, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	recorded := f.recorded()
	if len(recorded) != 1 {
		t.Fatalf("unexpected request count: %d", len(recorded))
	}

	req := recorded[0]
	if req.BkCloudID != 42 {
		t.Errorf("unexpected bk_cloud_id: %d", req.BkCloudID)
	}
	if req.DbCloudToken != "token" {
		t.Errorf("unexpected token: %s", req.DbCloudToken)
	}
	if len(req.Instances) != 1 {
		t.Fatalf("unexpected instance count: %d", len(req.Instances))
	}
	if req.Instances[0].IP != "1234" || req.Instances[0].Port != 0 || req.Instances[0].BkCloudID != 42 {
		t.Errorf("unexpected instance: %+v", req.Instances[0])
	}
	if len(req.Users) != 2 {
		t.Fatalf("unexpected user count: %d", len(req.Users))
	}
	for _, user := range req.Users {
		if user.UserName != userInstanceDefault {
			t.Errorf("unexpected username: %s", user.UserName)
		}
	}
	if want := 1*2 + 1; req.Limit != want {
		t.Errorf("unexpected limit, got: %d, want: %d", req.Limit, want)
	}
}

// respondEmptyPasswd answers every requested instance with an empty password.
func respondEmptyPasswd(user string) func(queryPasswdRequest) queryPasswdResponse {
	return func(req queryPasswdRequest) queryPasswdResponse {
		rsp := queryPasswdResponse{}
		for _, inst := range req.Instances {
			rsp.Data.Items = append(rsp.Data.Items, passwdItem{
				IP:        inst.IP,
				Component: componentRedis,
				UserName:  user,
				Password:  encodePasswd(""),
			})
		}
		return rsp
	}
}

func TestGetDbInstPasswd_EmptyPasswordIsValidAndCached(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)
	f.setRespond(respondEmptyPasswd(userInstanceDefault))

	// A cluster with no password configured is a legitimate answer, not a failure.
	passwd, err := GetDbInstPasswd(0, 9, haprobe.DbmMetadataMachineTypeTendisCache)
	if err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if passwd != "" {
		t.Fatalf("unexpected password: %s", passwd)
	}

	// It is cached like any other value, so the next caller is served locally.
	passwd, err = GetDbInstPasswd(0, 9, haprobe.DbmMetadataMachineTypeTendisCache)
	if err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if passwd != "" {
		t.Fatalf("unexpected password: %s", passwd)
	}
	if got := f.requestCount(); got != 1 {
		t.Fatalf("the empty password was not cached, requests: %d", got)
	}
}

func TestGetMachinePasswd_EmptyPasswordIsValidAndCached(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)
	f.setRespond(respondEmptyPasswd(userMachineDefault))

	passwd, err := GetMachinePasswd(1)
	if err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if passwd != "" {
		t.Fatalf("unexpected password: %s", passwd)
	}

	if _, err := GetMachinePasswd(1); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if got := f.requestCount(); got != 1 {
		t.Fatalf("the empty password was not cached, requests: %d", got)
	}
}

func TestBatchFill_SkipsClustersCachedWithEmptyPassword(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)
	f.setRespond(respondEmptyPasswd(userInstanceDefault))

	if _, err := GetDbInstPasswd(0, 20, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	if err := BatchFill(0, []int{20}); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if got := f.requestCount(); got != 1 {
		t.Fatalf("a cluster cached with an empty password was refetched, requests: %d", got)
	}
}

func TestGetDbInstPasswd_UndecodablePasswordFails(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	f.setRespond(func(req queryPasswdRequest) queryPasswdResponse {
		rsp := queryPasswdResponse{}
		rsp.Data.Items = append(rsp.Data.Items, passwdItem{
			IP:        req.Instances[0].IP,
			Component: componentRedis,
			UserName:  userInstanceDefault,
			Password:  "not-base64!!",
		})
		return rsp
	})

	if _, err := GetDbInstPasswd(0, 10, haprobe.DbmMetadataMachineTypeTendisCache); err == nil {
		t.Fatal("expected an error when the password cannot be decoded")
	}
}

func TestGetDbInstPasswd_ServiceErrorCodeFails(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	f.setRespond(func(queryPasswdRequest) queryPasswdResponse {
		return queryPasswdResponse{Code: 1, Message: "permission denied"}
	})

	_, err := GetDbInstPasswd(0, 11, haprobe.DbmMetadataMachineTypeTendisCache)
	if err == nil {
		t.Fatal("expected an error when the service reports a non-zero code")
	}
	if !strings.Contains(err.Error(), "permission denied") {
		t.Fatalf("the service message was dropped from the error: %s", err)
	}
}

func TestGetDbInstPasswd_BadHttpStatusIsRetriedThenFails(t *testing.T) {
	resetService(t)

	var attempts int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		atomic.AddInt32(&attempts, 1)
		http.Error(w, "boom", http.StatusInternalServerError)
	}))
	t.Cleanup(srv.Close)

	ApplyQueryConfig(QueryConfig{API: srv.URL, Token: "token", Timeout: 5 * time.Second})

	if _, err := GetDbInstPasswd(0, 12, haprobe.DbmMetadataMachineTypeTendisCache); err == nil {
		t.Fatal("expected an error on a non-200 response")
	}
	if got := atomic.LoadInt32(&attempts); got != queryAttempts {
		t.Fatalf("unexpected attempt count, got: %d, want: %d", got, queryAttempts)
	}
}

func TestGetDbInstPasswd_TransientFailureIsRetriedThenSucceeds(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)

	var attempts int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if atomic.AddInt32(&attempts, 1) == 1 {
			http.Error(w, "boom", http.StatusServiceUnavailable)
			return
		}
		f.Config.Handler.ServeHTTP(w, r)
	}))
	t.Cleanup(srv.Close)

	ApplyQueryConfig(QueryConfig{API: srv.URL, Token: "token", Timeout: 5 * time.Second})

	passwd, err := GetDbInstPasswd(0, 14, haprobe.DbmMetadataMachineTypeTendisCache)
	if err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if want := plainPasswd("14", componentRedis); passwd != want {
		t.Fatalf("unexpected password, got: %s, want: %s", passwd, want)
	}
	if got := atomic.LoadInt32(&attempts); got != 2 {
		t.Fatalf("unexpected attempt count, got: %d, want: 2", got)
	}
}

func TestGetDbInstPasswd_ConcurrentLookupsShareOneQuery(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	release := make(chan struct{})
	f.setRespond(func(req queryPasswdRequest) queryPasswdResponse {
		<-release
		return defaultRespond(req)
	})

	const goroutines = 16
	var wg sync.WaitGroup
	errs := make([]error, goroutines)
	passwds := make([]string, goroutines)

	for i := range goroutines {
		wg.Add(1)
		go func() {
			defer wg.Done()
			passwds[i], errs[i] = GetDbInstPasswd(0, 13, haprobe.DbmMetadataMachineTypeTendisCache)
		}()
	}

	// Give every goroutine a chance to join the in-flight query before it answers.
	time.Sleep(50 * time.Millisecond)
	close(release)
	wg.Wait()

	for i, err := range errs {
		if err != nil {
			t.Fatalf("goroutine %d failed: %s", i, err)
		}
		if want := plainPasswd("13", componentRedis); passwds[i] != want {
			t.Fatalf("goroutine %d got %s, want %s", i, passwds[i], want)
		}
	}

	if got := f.requestCount(); got != 1 {
		t.Fatalf("concurrent lookups were not collapsed, requests: %d", got)
	}
}

func TestApplyQueryConfig_DropsCachedPasswords(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	if _, err := GetDbInstPasswd(0, 14, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	configure(t, f)

	if _, err := GetDbInstPasswd(0, 14, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	if got := f.requestCount(); got != 2 {
		t.Fatalf("the cache survived a config change, requests: %d", got)
	}
}

func TestGetMachinePasswd_UsesFixedInstanceAndUser(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	passwd, err := GetMachinePasswd(42)
	if err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if want := plainPasswd(machineInstanceIP, componentRedis); passwd != want {
		t.Fatalf("unexpected password, got: %s, want: %s", passwd, want)
	}

	recorded := f.recorded()
	if len(recorded) != 1 {
		t.Fatalf("unexpected request count: %d", len(recorded))
	}

	req := recorded[0]
	if req.BkCloudID != 42 {
		t.Errorf("unexpected bk_cloud_id: %d", req.BkCloudID)
	}
	if len(req.Instances) != 1 || req.Instances[0].IP != machineInstanceIP || req.Instances[0].BkCloudID != 0 {
		t.Errorf("unexpected instances: %+v", req.Instances)
	}
	if len(req.Users) != 1 || req.Users[0].UserName != userMachineDefault {
		t.Errorf("unexpected users: %+v", req.Users)
	}

	if _, err := GetMachinePasswd(42); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if got := f.requestCount(); got != 1 {
		t.Fatalf("the machine password was not cached, requests: %d", got)
	}
}

func TestGetMachinePasswd_CachedPerCloudArea(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	if _, err := GetMachinePasswd(1); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if _, err := GetMachinePasswd(2); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	if got := f.requestCount(); got != 2 {
		t.Fatalf("cloud areas shared a cache entry, requests: %d", got)
	}
}

func TestGetMachinePasswd_NoItemsFails(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	f.setRespond(func(queryPasswdRequest) queryPasswdResponse {
		return queryPasswdResponse{}
	})

	if _, err := GetMachinePasswd(1); err == nil {
		t.Fatal("expected an error when the service returns no items")
	}
}

func TestBatchFill_SkipsCachedAndSplitsBatches(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	if _, err := GetDbInstPasswd(0, 1, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	clusterIDs := make([]int, 0, maxBatchInstances+40)
	for i := range maxBatchInstances + 40 {
		clusterIDs = append(clusterIDs, i+1)
	}
	// A duplicate must not consume a slot in any batch.
	clusterIDs = append(clusterIDs, 5)

	if err := BatchFill(0, clusterIDs); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}

	recorded := f.recorded()
	// Cluster 1, then the remaining 239 split into a full batch and a remainder.
	if len(recorded) != 3 {
		t.Fatalf("unexpected request count: %d", len(recorded))
	}
	if got := len(recorded[1].Instances); got != maxBatchInstances {
		t.Errorf("unexpected first batch size: %d", got)
	}
	if got := len(recorded[2].Instances); got != 39 {
		t.Errorf("unexpected second batch size: %d", got)
	}

	// Everything the prefetch covered is now served from cache.
	before := f.requestCount()
	for _, clusterID := range clusterIDs {
		if _, err := GetDbInstPasswd(0, clusterID, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
			t.Fatalf("unexpected error for cluster %d: %s", clusterID, err)
		}
	}
	if got := f.requestCount(); got != before {
		t.Fatalf("prefetched clusters still queried the service, requests: %d", got-before)
	}
}

func TestBatchFill_ReportsErrorButKeepsGoing(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	// The full batch keeps failing, the remainder always succeeds.
	f.setRespond(func(req queryPasswdRequest) queryPasswdResponse {
		if len(req.Instances) == maxBatchInstances {
			return queryPasswdResponse{Code: 1, Message: "broken"}
		}
		return defaultRespond(req)
	})

	clusterIDs := make([]int, 0, maxBatchInstances+1)
	for i := range maxBatchInstances + 1 {
		clusterIDs = append(clusterIDs, i+1)
	}

	if err := BatchFill(0, clusterIDs); err == nil {
		t.Fatal("expected the first batch failure to be reported")
	}

	if got := f.requestCount(); got != queryAttempts+1 {
		t.Fatalf("the second batch was skipped after the first failed, requests: %d", got)
	}

	// The batch that succeeded is cached even though the call returned an error.
	last := clusterIDs[len(clusterIDs)-1]
	before := f.requestCount()
	if _, err := GetDbInstPasswd(0, last, haprobe.DbmMetadataMachineTypeTendisCache); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if got := f.requestCount(); got != before {
		t.Fatal("the successful batch was not cached")
	}
}

func TestBatchFill_EmptyInputIssuesNoQuery(t *testing.T) {
	resetService(t)
	f := newFakePasswdServer(t)
	configure(t, f)

	if err := BatchFill(0, nil); err != nil {
		t.Fatalf("unexpected error: %s", err)
	}
	if got := f.requestCount(); got != 0 {
		t.Fatalf("an empty prefetch queried the service, requests: %d", got)
	}
}

func TestComponentName(t *testing.T) {
	cases := map[haprobe.DbmMetadataMachineType]string{
		haprobe.DbmMetadataMachineTypeTwemProxy:   componentRedisProxy,
		haprobe.DbmMetadataMachineTypePredixy:     componentRedisProxy,
		haprobe.DbmMetadataMachineTypeTendisCache: componentRedis,
		haprobe.DbmMetadataMachineTypeTendisPlus:  componentRedis,
		haprobe.DbmMetadataMachineTypeTendisSSD:   componentRedis,
		haprobe.DbmMetadataMachineType(""):        componentRedisProxyAdmin,
		haprobe.DbmMetadataMachineTypeBackend:     componentRedisProxyAdmin,
	}

	for machineType, want := range cases {
		if got := componentName(machineType); got != want {
			t.Errorf("componentName(%q) = %s, want %s", machineType, got, want)
		}
	}
}

func TestPasswdExpiration_StaysWithinJitterWindow(t *testing.T) {
	seen := map[time.Duration]struct{}{}

	for range 200 {
		ttl := passwdExpiration()
		if ttl < passwdTTL || ttl >= passwdTTL+passwdTTLJitter {
			t.Fatalf("ttl out of range: %s", ttl)
		}
		seen[ttl] = struct{}{}
	}

	if len(seen) < 2 {
		t.Fatal("the ttl is not jittered")
	}
}

func TestCacheKeys(t *testing.T) {
	if got := instanceCacheKey(1234, componentRedis); got != "1234-redis" {
		t.Errorf("unexpected instance key: %s", got)
	}
	if got := cacheKey("1234", componentRedis); got != "1234-redis" {
		t.Errorf("unexpected item key: %s", got)
	}
	if got := machineCacheKey(42); got != "machine-42" {
		t.Errorf("unexpected machine key: %s", got)
	}
}
