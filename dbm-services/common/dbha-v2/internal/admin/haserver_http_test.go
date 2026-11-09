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

package admin

import (
	"io"
	"net"
	"net/http"
	"strconv"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/admin/api/open"
	"dbm-services/common/dbha-v2/pkg/hanet"
)

// startHaServerWeb starts a web server wired like buildWeb (without swagger) and returns its base URL.
func startHaServerWeb(t *testing.T, storageAvailable bool) string {
	t.Helper()
	srv := newHaServerTestService(t, storageAvailable, nil)

	host, portText, err := net.SplitHostPort(freeGRPCAddress(t))
	if err != nil {
		t.Fatalf("split address failed, errmsg: %s", err)
	}
	port, _ := strconv.Atoi(portText)

	server := hanet.NewGinHTTPServer(&hanet.GinServerConfig{Host: host, Port: port})
	server.SetLifecycleMiddleware(srv.storageHTTPMiddleware())
	open.RegisterOpenAPI(srv.currentDBForContext, server)
	open.RegisterMetaAPI(&fakeHaServerLister{list: sampleHaServers()}, server)
	if err := server.Start(); err != nil {
		t.Fatalf("start web failed, errmsg: %s", err)
	}
	t.Cleanup(func() { _ = server.Stop() })

	return "http://" + net.JoinHostPort(host, portText)
}

type httpResult struct {
	status   int
	body     string
	location string
}

func doHaServerRequest(t *testing.T, method, url string) httpResult {
	t.Helper()
	client := &http.Client{CheckRedirect: func(*http.Request, []*http.Request) error {
		return http.ErrUseLastResponse
	}}

	req, err := http.NewRequest(method, url, nil)
	if err != nil {
		t.Fatalf("build request failed, errmsg: %s", err)
	}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("request failed, errmsg: %s", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	return httpResult{status: resp.StatusCode, body: string(body), location: resp.Header.Get("Location")}
}

func assertHaServersSuccess(t *testing.T, name string, got httpResult) {
	t.Helper()
	if got.status != http.StatusOK || !strings.HasPrefix(got.body, `{"data":{"servers":[{"role":"admin"`) ||
		!strings.HasSuffix(got.body, `"ips":["127.0.0.1","::1"]},"code":0,"message":""}`) {
		t.Fatalf("%s status: %d, body: %s", name, got.status, got.body)
	}
}

func TestHaServersRouting(t *testing.T) {
	base := startHaServerWeb(t, true)

	assertHaServersSuccess(t, "W01", doHaServerRequest(t, http.MethodGet, base+open.MetaHaServersPath))

	for _, method := range []string{http.MethodPost, http.MethodPut, http.MethodDelete} {
		if got := doHaServerRequest(t, method, base+open.MetaHaServersPath); got.status != http.StatusNotFound {
			t.Fatalf("W12 %s status: %d, body: %s", method, got.status, got.body)
		}
	}

	got := doHaServerRequest(t, http.MethodGet, base+open.MetaHaServersPath+"/")
	if got.status != http.StatusMovedPermanently || got.location != open.MetaHaServersPath ||
		strings.Contains(got.body, `"servers"`) {
		t.Fatalf("W13 status: %d, location: %s, body: %s", got.status, got.location, got.body)
	}

	for _, path := range []string{"/api/admin/meta/ha-server", "/api/admin/meta/"} {
		if got := doHaServerRequest(t, http.MethodGet, base+path); got.status != http.StatusNotFound {
			t.Fatalf("W14 %s status: %d", path, got.status)
		}
	}
}

func TestHaServersStorageIsolation(t *testing.T) {
	base := startHaServerWeb(t, false)

	assertHaServersSuccess(t, "W20", doHaServerRequest(t, http.MethodGet, base+open.MetaHaServersPath))

	cases := []struct {
		name   string
		method string
		path   string
	}{
		{"W21 existing strategy api", http.MethodGet, "/api/admin/strategies/"},
		{"W21 existing switch log api", http.MethodPost, "/api/admin/switchqueue/"},
		{"W22 non GET method", http.MethodPost, open.MetaHaServersPath},
		{"W23 exact match only", http.MethodGet, open.MetaHaServersPath + "-x"},
	}
	for _, tc := range cases {
		got := doHaServerRequest(t, tc.method, base+tc.path)
		if got.status != http.StatusServiceUnavailable || got.body != "" {
			t.Fatalf("%s status: %d, body: %s", tc.name, got.status, got.body)
		}
	}
}
