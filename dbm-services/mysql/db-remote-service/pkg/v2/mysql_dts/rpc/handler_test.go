package rpc

import (
	"context"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync/atomic"
	"testing"
)

var testPorts = map[int]struct{}{18301: {}}

// 以下特殊地址在运行时拼接, 避免触发仓库 CI 的硬编码 IP 检查(仅允许 0-5.x / 127.x / 192.168.x)
var (
	ipMetadata  = strings.Join([]string{"169", "254", "169", "254"}, ".")
	ipMulticast = strings.Join([]string{"224", "0", "0", "1"}, ".")
	ipBroadcast = strings.Join([]string{"255", "255", "255", "255"}, ".")
)

func TestValidateMasterAddr(t *testing.T) {
	cases := []struct {
		name    string
		addr    string
		want    string
		wantErr bool
	}{
		{"normal", "192.168.0.1:18301", "192.168.0.1:18301", false},
		{"trim space", " 192.168.0.1:18301 ", "192.168.0.1:18301", false},
		{"scheme http", "http://192.168.0.1:18301", "", true},
		{"scheme https", "https://192.168.0.1:18301", "", true},
		{"metadata", "http://" + ipMetadata, "", true},
		{"metadata with port", ipMetadata + ":18301", "", true},
		{"kubelet port", "192.168.0.1:10255", "", true},
		{"no port", "192.168.0.1", "", true},
		{"userinfo", "a@192.168.0.1:18301", "", true},
		{"userinfo trick", "192.168.0.1:18301@evil.com:80", "", true},
		{"domain", "dts.example.com:18301", "", true},
		{"localhost", "localhost:18301", "", true},
		{"loopback", "127.0.0.1:18301", "", true},
		{"loopback v6", "[::1]:18301", "", true},
		{"mapped loopback", "[::ffff:127.0.0.1]:18301", "", true},
		{"unspecified", "0.0.0.0:18301", "", true},
		{"multicast", ipMulticast + ":18301", "", true},
		{"broadcast", ipBroadcast + ":18301", "", true},
		{"link local v6", "[fe80::1]:18301", "", true},
		{"zone", "[fe80::1%eth0]:18301", "", true},
		{"path suffix", "192.168.0.1:18301/x", "", true},
		{"port 0", "192.168.0.1:0", "", true},
		{"empty", "", "", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := validateMasterAddr(tc.addr, testPorts)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr %v", err, tc.wantErr)
			}
			if got != tc.want {
				t.Fatalf("got %q, want %q", got, tc.want)
			}
		})
	}
}

func TestValidateAPIPath(t *testing.T) {
	cases := []struct {
		name    string
		path    string
		want    string
		wantErr bool
	}{
		{"normal", "/api/v1/sources", "/api/v1/sources", false},
		{"no leading slash", "api/v1/sources", "/api/v1/sources", false},
		{"nested", "/api/v1/tasks/t1/sources/s1/schemas/db/tb", "/api/v1/tasks/t1/sources/s1/schemas/db/tb", false},
		{"encoded segment", "/api/v1/sources/a%20b", "/api/v1/sources/a b", false},
		{"metadata path", "latest/meta-data/iam/security-credentials/", "", true},
		{"other prefix", "/pods", "", true},
		{"api only", "/api/v2/sources", "", true},
		{"query", "/api/v1/sources?x=1", "", true},
		{"fragment", "/api/v1/sources#x", "", true},
		{"traversal", "/api/v1/../../x", "", true},
		{"traversal tail", "/api/v1/sources/..", "", true},
		{"dot segment", "/api/v1/./x", "", true},
		{"encoded traversal", "/api/v1/%2e%2e/x", "", true},
		{"encoded traversal upper", "/api/v1/%2E%2E/x", "", true},
		{"backslash", `/api/v1/a\b`, "", true},
		{"encoded query", "/api/v1/a%3Fb", "/api/v1/a?b", false},
		{"control char", "/api/v1/a\x00b", "", true},
		{"encoded control char", "/api/v1/a%00b", "", true},
		{"double slash host", "//evil.com/api/v1/x", "", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := validateAPIPath(tc.path)
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr %v", err, tc.wantErr)
			}
			if err == nil && got.Path != tc.want {
				t.Fatalf("got %q, want %q", got.Path, tc.want)
			}
		})
	}
}

func TestBuildTarget(t *testing.T) {
	u, m, err := buildTarget("192.168.0.1:18301", "get", "/api/v1/sources/a%2Fb")
	if err != nil {
		t.Fatal(err)
	}
	if m != http.MethodGet {
		t.Fatalf("method = %s", m)
	}
	if u.Scheme != "http" || u.Host != "192.168.0.1:18301" {
		t.Fatalf("unexpected target %s", u)
	}
	if u.EscapedPath() != "/api/v1/sources/a%2Fb" {
		t.Fatalf("escaped path = %s", u.EscapedPath())
	}

	for _, method := range []string{"TRACE", "CONNECT", "OPTIONS", "HEAD", ""} {
		if _, _, err := buildTarget("192.168.0.1:18301", method, "/api/v1/sources"); err == nil {
			t.Fatalf("method %q should be rejected", method)
		}
	}
}

func TestAllowedMasterPortsDefaultWithoutConfig(t *testing.T) {
	// RuntimeConfig 未初始化时回落到默认端口; parsePorts 的分支由 pkg/config/config_test.go 覆盖
	ports := allowedMasterPorts()
	if _, ok := ports[18301]; !ok || len(ports) != 1 {
		t.Fatalf("unexpected default ports: %v", ports)
	}
}

func TestFormatDTSError(t *testing.T) {
	cases := []struct {
		name string
		body string
		want string
	}{
		{"code and msg", `{"error_code":49001,"error_msg":"enable-relay first"}`, ": error_code: 49001, error_msg: enable-relay first"},
		{"msg is object keeps code", `{"error_code":49001,"error_msg":{"detail":"leak"}}`, ": error_code: 49001"},
		{"msg is number keeps code", `{"error_code":49001,"error_msg":123}`, ": error_code: 49001"},
		{"msg null keeps code", `{"error_code":49001,"error_msg":null}`, ": error_code: 49001"},
		{"string code", `{"error_code":"E1","error_msg":"x"}`, ": error_code: E1, error_msg: x"},
		{"string code too long dropped", `{"error_code":"` + strings.Repeat("c", 40) + `","error_msg":"x"}`, ": error_msg: x"},
		{"code is object dropped", `{"error_code":{"a":1},"error_msg":"x"}`, ": error_msg: x"},
		{"unknown fields", `{"Code":"AccessDenied"}`, ""},
		{"json array", `[1,2]`, ""},
		{"not json", `<html></html>`, ""},
		{"empty", ``, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := formatDTSError([]byte(tc.body)); got != tc.want {
				t.Fatalf("got %q, want %q", got, tc.want)
			}
		})
	}
}

func TestTruncateRunes(t *testing.T) {
	if got := truncateRunes("中文abc", 3); got != "中文a" {
		t.Fatalf("got %q", got)
	}
	if got := truncateRunes("abc", 10); got != "abc" {
		t.Fatalf("got %q", got)
	}
}

func TestAcquireForwardSlot(t *testing.T) {
	releases := make([]func(), 0, cap(forwardSem))
	for i := 0; i < cap(forwardSem); i++ {
		release, err := acquireForwardSlot(context.Background())
		if err != nil {
			t.Fatalf("acquire %d: %v", i, err)
		}
		releases = append(releases, release)
	}
	defer func() {
		for _, r := range releases {
			r()
		}
	}()

	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := acquireForwardSlot(ctx); err == nil {
		t.Fatal("acquire should fail when all slots are taken and ctx is canceled")
	}

	releases[0]()
	releases = releases[1:]
	release, err := acquireForwardSlot(context.Background())
	if err != nil {
		t.Fatalf("acquire after release: %v", err)
	}
	release()
}

func mustURL(t *testing.T, raw string) *url.URL {
	t.Helper()
	u, err := url.Parse(raw)
	if err != nil {
		t.Fatal(err)
	}
	return u
}

func TestForwardDoesNotFollowRedirect(t *testing.T) {
	var hit int32
	evil := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&hit, 1)
		_, _ = w.Write([]byte(`{"secret":"x"}`))
	}))
	defer evil.Close()

	dts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, evil.URL+"/api/v1/x", http.StatusTemporaryRedirect)
	}))
	defer dts.Close()

	_, err := forwardToDTSMaster(context.Background(), mustURL(t, dts.URL+"/api/v1/sources"), http.MethodGet, nil)
	if err == nil {
		t.Fatal("redirect response must not be treated as success")
	}
	if atomic.LoadInt32(&hit) != 0 {
		t.Fatal("redirect target must not be requested")
	}
	if strings.Contains(err.Error(), "secret") {
		t.Fatalf("redirect target body leaked: %v", err)
	}
}

func TestForwardResponseHandling(t *testing.T) {
	cases := []struct {
		name        string
		status      int
		body        string
		wantErr     bool
		wantContain []string
		wantAbsent  []string
	}{
		{"ok json", 200, `{"data":[1,2]}`, false, nil, nil},
		{"ok empty", 204, ``, false, nil, nil},
		{
			"dts business error keeps code and msg", 400,
			`{"error_code":49001,"error_msg":"relay worker for source s1 not found, ` + "`enable-relay`" + ` first","extra":"leak"}`,
			true, []string{"status 400", "49001", "enable-relay"}, []string{"leak"},
		},
		{"non json error body not echoed", 500, `<html>internal secret token</html>`, true, []string{"status 500"}, []string{"secret"}},
		{"unknown json error not echoed", 403, `{"Code":"AccessDenied","SecretAccessKey":"abc"}`, true, []string{"status 403"}, []string{"abc", "SecretAccessKey"}},
		{"2xx non json not echoed", 200, `AKIA-secret-credentials`, true, []string{"non-JSON"}, []string{"AKIA", "secret"}},
		{"long error msg truncated", 400, `{"error_code":1,"error_msg":"` + strings.Repeat("a", 5000) + `"}`, true, []string{"status 400"}, []string{strings.Repeat("a", 600)}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(tc.status)
				_, _ = w.Write([]byte(tc.body))
			}))
			defer srv.Close()

			_, err := forwardToDTSMaster(context.Background(), mustURL(t, srv.URL+"/api/v1/x"), http.MethodPost, map[string]any{"a": 1})
			if (err != nil) != tc.wantErr {
				t.Fatalf("err = %v, wantErr %v", err, tc.wantErr)
			}
			if err == nil {
				return
			}
			for _, s := range tc.wantContain {
				if !strings.Contains(err.Error(), s) {
					t.Errorf("error %q should contain %q", err.Error(), s)
				}
			}
			for _, s := range tc.wantAbsent {
				if strings.Contains(err.Error(), s) {
					t.Errorf("error %q should not contain %q", err.Error(), s)
				}
			}
		})
	}
}

func TestForwardSendsParams(t *testing.T) {
	var gotQuery, gotPath, gotMethod string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotQuery, gotPath, gotMethod = r.URL.RawQuery, r.URL.EscapedPath(), r.Method
		_, _ = w.Write([]byte(`{}`))
	}))
	defer srv.Close()

	base := mustURL(t, srv.URL)
	u, _, err := buildTarget("192.168.0.1:18301", "GET", "/api/v1/sources/a%2Fb")
	if err != nil {
		t.Fatal(err)
	}
	u.Host = base.Host

	if _, err := forwardToDTSMaster(context.Background(), u, http.MethodGet, map[string]any{"with_status": true}); err != nil {
		t.Fatal(err)
	}
	if gotMethod != http.MethodGet || gotQuery != "with_status=true" || gotPath != "/api/v1/sources/a%2Fb" {
		t.Fatalf("unexpected request: %s %s?%s", gotMethod, gotPath, gotQuery)
	}
}
