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

package handler

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

const testHaServersPath = "/api/admin/meta/ha-servers"

const rawDiscoveryError = "dial tcp 127.0.0.1:2379: connect: connection refused"

type fakeHaServerLister struct {
	list *discovery.HaServerList
	err  error
}

func (f *fakeHaServerLister) List(context.Context) (*discovery.HaServerList, error) {
	return f.list, f.err
}

func sampleList() *discovery.HaServerList {
	start := time.Date(2026, 11, 4, 6, 0, 0, 0, time.UTC)
	return &discovery.HaServerList{
		Servers: []discovery.HaServer{{
			Role: "admin", ID: "admin-1", IPs: []string{"127.0.0.1"},
			StartTime: start, UpdatedAt: start.Add(30 * time.Minute), Uptime: "30 minutes",
		}},
		IPs: []string{"127.0.0.1", "::1"},
	}
}

func serveHaServers(t *testing.T, lister HaServerLister, req *http.Request) *httptest.ResponseRecorder {
	t.Helper()
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET(testHaServersPath, NewHaServerHandler(lister).List)

	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, req)

	return recorder
}

func decodeTopLevel(t *testing.T, body []byte) map[string]json.RawMessage {
	t.Helper()
	top := map[string]json.RawMessage{}
	if err := json.Unmarshal(body, &top); err != nil {
		t.Fatalf("decode body failed, errmsg: %s, body: %s", err, body)
	}

	return top
}

func TestHaServerHandlerSuccess(t *testing.T) {
	want := `{"data":{"servers":[{"role":"admin","id":"admin-1","ips":["127.0.0.1"],` +
		`"start_time":"2026-11-04T14:00:00+08:00","updated_at":"2026-11-04T14:30:00+08:00",` +
		`"uptime":"30 minutes"}],"ips":["127.0.0.1","::1"]},"code":0,"message":""}`

	requests := map[string]*http.Request{
		"W01 plain":       httptest.NewRequest(http.MethodGet, testHaServersPath, nil),
		"W10 with query":  httptest.NewRequest(http.MethodGet, testHaServersPath+"?role=admin&limit=1", nil),
		"W11 with a body": httptest.NewRequest(http.MethodGet, testHaServersPath, strings.NewReader(`{"role":"x"}`)),
	}
	for name, req := range requests {
		recorder := serveHaServers(t, &fakeHaServerLister{list: sampleList()}, req)
		if recorder.Code != http.StatusOK {
			t.Fatalf("%s status: %d", name, recorder.Code)
		}
		if got := recorder.Body.String(); got != want {
			t.Fatalf("%s body: %s, want: %s", name, got, want)
		}
		if ct := recorder.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
			t.Fatalf("W04 %s content type: %s", name, ct)
		}
		if top := decodeTopLevel(t, recorder.Body.Bytes()); len(top) != 3 {
			t.Fatalf("W01 %s top level keys: %v", name, top)
		}
	}
}

func TestHaServerHandlerEmpty(t *testing.T) {
	for name, list := range map[string]*discovery.HaServerList{
		"nil":   nil,
		"empty": {Servers: []discovery.HaServer{}, IPs: []string{}},
	} {
		req := httptest.NewRequest(http.MethodGet, testHaServersPath, nil)
		recorder := serveHaServers(t, &fakeHaServerLister{list: list}, req)
		want := `{"data":{"servers":[],"ips":[]},"code":0,"message":""}`
		if recorder.Code != http.StatusOK || recorder.Body.String() != want {
			t.Fatalf("W02 %s status: %d, body: %s", name, recorder.Code, recorder.Body.String())
		}
	}
}

type warnCaptureLogger struct {
	mu   sync.Mutex
	warn []string
}

func installWarnCaptureLogger(t *testing.T) *warnCaptureLogger {
	t.Helper()
	prev := logger.Log()
	capture := &warnCaptureLogger{}
	logger.SetLogger(capture)
	t.Cleanup(func() { logger.SetLogger(prev) })

	return capture
}

func (l *warnCaptureLogger) OriginLogger() *zap.Logger { return zap.NewNop() }

func (l *warnCaptureLogger) Debug(string, ...any) {}
func (l *warnCaptureLogger) Info(string, ...any)  {}
func (l *warnCaptureLogger) Error(string, ...any) {}
func (l *warnCaptureLogger) Fatal(string, ...any) {}

func (l *warnCaptureLogger) Warn(format string, args ...any) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.warn = append(l.warn, fmt.Sprintf(format, args...))
}

func (l *warnCaptureLogger) warnMessages() []string {
	l.mu.Lock()
	defer l.mu.Unlock()
	out := make([]string, len(l.warn))
	copy(out, l.warn)

	return out
}

func TestHaServerHandlerDiscoveryFailure(t *testing.T) {
	capture := installWarnCaptureLogger(t)
	req := httptest.NewRequest(http.MethodGet, testHaServersPath, nil)
	recorder := serveHaServers(t, &fakeHaServerLister{err: errors.New(rawDiscoveryError)}, req)

	wantLog := "list ha servers failed, errmsg: " + rawDiscoveryError
	if logs := capture.warnMessages(); len(logs) != 1 || logs[0] != wantLog {
		t.Fatalf("W03 warn logs: %q, want exactly: %q", logs, wantLog)
	}

	want := `{"data":"","code":1,"message":"service discovery unavailable"}`
	if recorder.Code != http.StatusBadRequest || recorder.Body.String() != want {
		t.Fatalf("W03 status: %d, body: %s", recorder.Code, recorder.Body.String())
	}
	if strings.Contains(recorder.Body.String(), "127.0.0.1") {
		t.Fatalf("W03 raw error leaked: %s", recorder.Body.String())
	}
	if ct := recorder.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Fatalf("W04 content type: %s", ct)
	}
}
