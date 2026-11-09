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
	"encoding/json"
	"errors"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/constant"
)

type fakePrefixReader struct {
	mu       sync.Mutex
	data     map[string]map[string][]byte
	errs     map[string]error
	block    bool
	prefixes []string
}

func (f *fakePrefixReader) GetWithPrefix(ctx context.Context, key string) (map[string][]byte, error) {
	f.mu.Lock()
	f.prefixes = append(f.prefixes, key)
	f.mu.Unlock()

	if f.block {
		<-ctx.Done()
		return nil, ctx.Err()
	}

	if err := f.errs[key]; err != nil {
		return nil, err
	}

	return f.data[key], nil
}

var testStartTime = time.Date(2026, 11, 4, 6, 0, 0, 0, time.UTC)

func haServerKey(role, id string) string {
	return HaServerSelfPrefix(role) + etcdKeySeparator + id
}

func haServerValue(t *testing.T, name, id string, ips ...string) []byte {
	t.Helper()
	data, err := json.Marshal(ServiceInfo{
		ID: id, Name: name, IPs: ips,
		StartTime: testStartTime, UpdatedAt: testStartTime.Add(30 * time.Minute), Uptime: "30 minutes",
	})
	if err != nil {
		t.Fatalf("marshal service info failed, errmsg: %s", err)
	}

	return data
}

func wantHaServer(role, id string, ips ...string) HaServer {
	return HaServer{
		Role: role, ID: id, IPs: ips,
		StartTime: testStartTime, UpdatedAt: testStartTime.Add(30 * time.Minute), Uptime: "30 minutes",
	}
}

func assertHaServerList(t *testing.T, got *HaServerList, wantServers []HaServer, wantIPs []string) {
	t.Helper()
	if got == nil || got.Servers == nil || got.IPs == nil {
		t.Fatalf("result and its slices must be non-nil, got: %+v", got)
	}

	if len(got.Servers) != len(wantServers) {
		t.Fatalf("servers count: %d, want: %d, got: %+v", len(got.Servers), len(wantServers), got.Servers)
	}

	for i := range wantServers {
		g, w := got.Servers[i], wantServers[i]
		if g.Role != w.Role || g.ID != w.ID || g.Uptime != w.Uptime || !reflect.DeepEqual(g.IPs, w.IPs) ||
			!g.StartTime.Equal(w.StartTime) || !g.UpdatedAt.Equal(w.UpdatedAt) {
			t.Fatalf("server[%d]: %+v, want: %+v", i, g, w)
		}
	}

	if !reflect.DeepEqual(got.IPs, wantIPs) {
		t.Fatalf("ips: %v, want: %v", got.IPs, wantIPs)
	}
}

func TestParseHaServersNormal(t *testing.T) {
	cases := []struct {
		name        string
		kvs         func(t *testing.T) map[string][]byte
		wantServers []HaServer
		wantIPs     []string
	}{
		{
			name: "D01 three roles ordered by role",
			kvs: func(t *testing.T) map[string][]byte {
				return map[string][]byte{
					haServerKey("receiver", "r1"): haServerValue(t, "receiver", "r1", "127.0.0.1"),
					haServerKey("admin", "a1"):    haServerValue(t, "admin", "a1", "127.0.0.1"),
					haServerKey("analysis", "n1"): haServerValue(t, "analysis", "n1", "127.0.0.1"),
				}
			},
			wantServers: []HaServer{
				wantHaServer("admin", "a1", "127.0.0.1"),
				wantHaServer("analysis", "n1", "127.0.0.1"),
				wantHaServer("receiver", "r1", "127.0.0.1"),
			},
			wantIPs: []string{"127.0.0.1"},
		},
		{
			name: "D02 same role ordered by id",
			kvs: func(t *testing.T) map[string][]byte {
				return map[string][]byte{
					haServerKey("analysis", "n2"): haServerValue(t, "analysis", "n2", "127.0.0.1"),
					haServerKey("analysis", "n1"): haServerValue(t, "analysis", "n1", "127.0.0.1"),
				}
			},
			wantServers: []HaServer{
				wantHaServer("analysis", "n1", "127.0.0.1"),
				wantHaServer("analysis", "n2", "127.0.0.1"),
			},
			wantIPs: []string{"127.0.0.1"},
		},
		{
			name: "D03 D05 multiple ips sorted and deduplicated",
			kvs: func(t *testing.T) map[string][]byte {
				return map[string][]byte{
					haServerKey("admin", "a1"):    haServerValue(t, "admin", "a1", "::1", "127.0.0.1"),
					haServerKey("receiver", "r1"): haServerValue(t, "receiver", "r1", "::1"),
				}
			},
			wantServers: []HaServer{
				wantHaServer("admin", "a1", "127.0.0.1", "::1"),
				wantHaServer("receiver", "r1", "::1"),
			},
			wantIPs: []string{"127.0.0.1", "::1"},
		},
		{
			name: "D04 same host multiple roles",
			kvs: func(t *testing.T) map[string][]byte {
				return map[string][]byte{
					haServerKey("admin", "a1"):    haServerValue(t, "admin", "a1", "127.0.0.1"),
					haServerKey("analysis", "n1"): haServerValue(t, "analysis", "n1", "127.0.0.1"),
				}
			},
			wantServers: []HaServer{
				wantHaServer("admin", "a1", "127.0.0.1"),
				wantHaServer("analysis", "n1", "127.0.0.1"),
			},
			wantIPs: []string{"127.0.0.1"},
		},
		{
			name:        "D06 empty input",
			kvs:         func(*testing.T) map[string][]byte { return nil },
			wantServers: []HaServer{},
			wantIPs:     []string{},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			assertHaServerList(t, ParseHaServers(tc.kvs(t)), tc.wantServers, tc.wantIPs)
		})
	}
}

func TestParseHaServersStableOrder(t *testing.T) {
	kvs := map[string][]byte{}
	for _, id := range []string{"c", "a", "b"} {
		for _, role := range HaServerRoles() {
			kvs[haServerKey(role, id)] = haServerValue(t, role, id, "::1", "127.0.0.1")
		}
	}

	first := ParseHaServers(kvs)
	for i := 0; i < 20; i++ {
		got := ParseHaServers(kvs)
		if !reflect.DeepEqual(got, first) {
			t.Fatalf("D07 run %d differs, got: %+v, want: %+v", i, got, first)
		}
	}

	if first.Servers[0].Role != HaServerRoleAdmin || first.Servers[0].ID != "a" ||
		first.Servers[8].Role != HaServerRoleReceiver || first.Servers[8].ID != "c" {
		t.Fatalf("D07 unexpected order: %+v", first.Servers)
	}
}

func TestParseHaServersSkipInvalid(t *testing.T) {
	valid := haServerKey("admin", "a1")
	cases := []struct {
		name  string
		key   string
		value func(t *testing.T) []byte
	}{
		{"D10 unknown role", "/dbha/registry/probe/self/p1", nil},
		{"D11 mutex key", "/dbha/registry/analysis/mutex/m1", nil},
		{"D11 election key", "/dbha/registry/analysis/election/leader", nil},
		{"D12 missing id", "/dbha/registry/analysis/self", nil},
		{"D12 empty id segment", "/dbha/registry/analysis/self/", nil},
		{"D13 extra segment", "/dbha/registry/analysis/self/n1/extra", nil},
		{"D14 similar role prefix", "/dbha/registry/analysisx/self/n1", nil},
		{"D14 other root", "/dbha/registryx/analysis/self/n1", nil},
		{"D20 empty value", haServerKey("analysis", "n1"), func(*testing.T) []byte { return []byte{} }},
		{"D21 invalid json", haServerKey("analysis", "n1"), func(*testing.T) []byte { return []byte("{bad") }},
		{"D22 name mismatch", haServerKey("analysis", "n1"), func(t *testing.T) []byte {
			return haServerValue(t, "receiver", "n1", "127.0.0.1")
		}},
		{"D23 empty id", haServerKey("analysis", "n1"), func(t *testing.T) []byte {
			return haServerValue(t, "analysis", "", "127.0.0.1")
		}},
		{"D24 no ips", haServerKey("analysis", "n1"), func(t *testing.T) []byte {
			return haServerValue(t, "analysis", "n1")
		}},
		{"D26 only empty ips", haServerKey("analysis", "n1"), func(t *testing.T) []byte {
			return haServerValue(t, "analysis", "n1", "", "")
		}},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			value := haServerValue(t, "analysis", "n1", "::1")
			if tc.value != nil {
				value = tc.value(t)
			}

			kvs := map[string][]byte{tc.key: value, valid: haServerValue(t, "admin", "a1", "127.0.0.1")}
			assertHaServerList(t, ParseHaServers(kvs),
				[]HaServer{wantHaServer("admin", "a1", "127.0.0.1")}, []string{"127.0.0.1"})
		})
	}
}

func TestParseHaServersSkipLogs(t *testing.T) {
	const secretValue = "secret-value-marker"
	key := haServerKey("analysis", "n1")
	cases := []struct {
		name      string
		key       string
		value     func(t *testing.T) []byte
		wantLevel string
		wantMsg   string
	}{
		{"D10 invalid key", "/dbha/registry/probe/self/p1", func(t *testing.T) []byte {
			return haServerValue(t, "probe", secretValue, "127.0.0.1")
		}, "warn", "skip ha server registration, key: /dbha/registry/probe/self/p1, reason: invalid key"},
		{"D20 empty value", key, func(*testing.T) []byte { return []byte{} },
			"debug", "skip ha server registration, key: " + key + ", reason: empty value"},
		{"D21 invalid json", key, func(*testing.T) []byte { return []byte("{" + secretValue) },
			"warn", "skip ha server registration, key: " + key + ", reason: invalid json, errmsg: "},
		{"D22 name mismatch", key, func(t *testing.T) []byte {
			return haServerValue(t, "receiver", secretValue, "127.0.0.1")
		}, "warn", "skip ha server registration, key: " + key + ", reason: name does not match key role"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			capture := installCaptureLogger(t)
			ParseHaServers(map[string][]byte{tc.key: tc.value(t)})

			logs := capture.logs()
			if len(logs) != 1 {
				t.Fatalf("log count: %d, want: 1, logs: %+v", len(logs), logs)
			}
			if logs[0].level != tc.wantLevel || !strings.HasPrefix(logs[0].message, tc.wantMsg) {
				t.Fatalf("log: %+v, want level: %s, prefix: %s", logs[0], tc.wantLevel, tc.wantMsg)
			}
			if strings.Contains(logs[0].message, secretValue) {
				t.Fatalf("log must not contain registration value, got: %s", logs[0].message)
			}
		})
	}
}

func TestParseHaServersDropEmptyIPs(t *testing.T) {
	kvs := map[string][]byte{
		haServerKey("analysis", "n1"): haServerValue(t, "analysis", "n1", "", "::1", "", "127.0.0.1"),
		haServerKey("probe", "p1"):    haServerValue(t, "probe", "p1", "127.0.0.1"),
		haServerKey("receiver", "r1"): []byte("null"),
	}

	assertHaServerList(t, ParseHaServers(kvs),
		[]HaServer{wantHaServer("analysis", "n1", "127.0.0.1", "::1")}, []string{"127.0.0.1", "::1"})
}

func TestHaServerSelfPrefix(t *testing.T) {
	want := map[string]string{
		HaServerRoleAdmin:    "/dbha/registry/admin/self",
		HaServerRoleAnalysis: "/dbha/registry/analysis/self",
		HaServerRoleReceiver: "/dbha/registry/receiver/self",
	}
	for role, prefix := range want {
		if got := HaServerSelfPrefix(role); got != prefix {
			t.Fatalf("L10 prefix of %s: %s, want: %s", role, got, prefix)
		}
	}

	if got := HaServerRoles(); !reflect.DeepEqual(got, []string{"admin", "analysis", "receiver"}) {
		t.Fatalf("roles: %v", got)
	}
}

func TestListHaServersReadsAllPrefixes(t *testing.T) {
	reader := &fakePrefixReader{data: map[string]map[string][]byte{
		HaServerSelfPrefix("admin"): {haServerKey("admin", "a1"): haServerValue(t, "admin", "a1", "127.0.0.1")},
		HaServerSelfPrefix("receiver"): {
			haServerKey("receiver", "r1"): haServerValue(t, "receiver", "r1", "::1"),
		},
	}}

	got, err := ListHaServers(context.Background(), reader, time.Second)
	if err != nil {
		t.Fatalf("L01 unexpected error, errmsg: %s", err)
	}

	assertHaServerList(t, got,
		[]HaServer{wantHaServer("admin", "a1", "127.0.0.1"), wantHaServer("receiver", "r1", "::1")},
		[]string{"127.0.0.1", "::1"})

	wantPrefixes := map[string]bool{}
	for _, role := range HaServerRoles() {
		wantPrefixes[HaServerSelfPrefix(role)] = true
	}
	if len(reader.prefixes) != len(wantPrefixes) {
		t.Fatalf("L01 read prefixes: %v", reader.prefixes)
	}
	for _, p := range reader.prefixes {
		if !wantPrefixes[p] {
			t.Fatalf("L01 unexpected prefix: %s", p)
		}
	}
}

func TestListHaServersFailures(t *testing.T) {
	adminData := map[string]map[string][]byte{
		HaServerSelfPrefix("admin"): {haServerKey("admin", "a1"): haServerValue(t, "admin", "a1", "127.0.0.1")},
	}
	readErr := errors.New("etcd read failed")

	t.Run("L02 any prefix error fails whole call", func(t *testing.T) {
		reader := &fakePrefixReader{data: adminData, errs: map[string]error{HaServerSelfPrefix("receiver"): readErr}}
		got, err := ListHaServers(context.Background(), reader, time.Second)
		if !errors.Is(err, readErr) || got != nil {
			t.Fatalf("got: %+v, err: %v", got, err)
		}
	})

	t.Run("L03 request timeout", func(t *testing.T) {
		reader := &fakePrefixReader{block: true}
		start := time.Now()
		got, err := ListHaServers(context.Background(), reader, 50*time.Millisecond)
		if !errors.Is(err, context.DeadlineExceeded) || got != nil {
			t.Fatalf("got: %+v, err: %v", got, err)
		}
		if elapsed := time.Since(start); elapsed > time.Second {
			t.Fatalf("timeout is not shared by all prefixes, elapsed: %s", elapsed)
		}
	})

	t.Run("L03 caller context canceled", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		cancel()
		got, err := ListHaServers(ctx, &fakePrefixReader{block: true}, time.Second)
		if !errors.Is(err, context.Canceled) || got != nil {
			t.Fatalf("got: %+v, err: %v", got, err)
		}
	})

	t.Run("L04 all prefixes empty", func(t *testing.T) {
		got, err := ListHaServers(context.Background(), &fakePrefixReader{}, time.Second)
		if err != nil {
			t.Fatalf("unexpected error, errmsg: %s", err)
		}
		assertHaServerList(t, got, []HaServer{}, []string{})
	})
}

type deadlineReader struct {
	deadline time.Duration
}

func (r *deadlineReader) GetWithPrefix(ctx context.Context, _ string) (map[string][]byte, error) {
	if dl, ok := ctx.Deadline(); ok {
		r.deadline = time.Until(dl)
	}

	return nil, nil
}

func TestListHaServersTimeoutSource(t *testing.T) {
	cases := []struct {
		name    string
		timeout time.Duration
		want    time.Duration
	}{
		{"L05 configured timeout", 10 * time.Second, 10 * time.Second},
		{"L05 zero falls back to default", 0, constant.DefaultServiceUpdateTimeout},
		{"L05 negative falls back to default", -time.Second, constant.DefaultServiceUpdateTimeout},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			reader := &deadlineReader{}
			if _, err := ListHaServers(context.Background(), reader, tc.timeout); err != nil {
				t.Fatalf("unexpected error, errmsg: %s", err)
			}
			if reader.deadline > tc.want || reader.deadline < tc.want-time.Second {
				t.Fatalf("deadline: %s, want about: %s", reader.deadline, tc.want)
			}
		})
	}
}
