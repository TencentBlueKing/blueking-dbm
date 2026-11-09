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

package main

import (
	"context"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
)

func freeLoopbackAddr(t *testing.T) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed, errmsg: %s", err)
	}
	addr := ln.Addr().String()
	_ = ln.Close()

	return addr
}

func doControl(t *testing.T, mux *http.ServeMux, method, target, body string) int {
	t.Helper()
	recorder := httptest.NewRecorder()
	mux.ServeHTTP(recorder, httptest.NewRequest(method, target, strings.NewReader(body)))

	return recorder.Code
}

func etcdGet(t *testing.T, addr, key string) (string, error) {
	t.Helper()
	cli, err := clientv3.New(clientv3.Config{Endpoints: []string{addr}, DialTimeout: time.Second})
	if err != nil {
		return "", err
	}
	defer cli.Close()

	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	resp, err := cli.Get(ctx, key)
	if err != nil || len(resp.Kvs) == 0 {
		return "", err
	}

	return string(resp.Kvs[0].Value), nil
}

func TestDepControlEtcdKVAndRestart(t *testing.T) {
	ctl := newDepControl(freeLoopbackAddr(t), freeLoopbackAddr(t))
	defer ctl.stopAll()
	if err := ctl.startEtcd(); err != nil {
		t.Fatalf("start etcd failed, errmsg: %s", err)
	}

	mux := http.NewServeMux()
	ctl.registerControlHandlers(mux)
	key := "/dbha/registry/receiver/self/r1"

	if code := doControl(t, mux, http.MethodPut, controlEtcdKVPath+"?key="+key, `{"id":"r1"}`); code != 204 {
		t.Fatalf("put status: %d", code)
	}
	if got, err := etcdGet(t, ctl.etcdAddr, key); err != nil || got != `{"id":"r1"}` {
		t.Fatalf("get after put: %q, err: %v", got, err)
	}

	if code := doControl(t, mux, http.MethodPost, controlEtcdStopPath, ""); code != 204 {
		t.Fatalf("stop status: %d", code)
	}
	if _, err := etcdGet(t, ctl.etcdAddr, key); err == nil {
		t.Fatal("get should fail while etcd is stopped")
	}

	if code := doControl(t, mux, http.MethodPost, controlEtcdStartPath, ""); code != 204 {
		t.Fatalf("start status: %d", code)
	}
	if got, err := etcdGet(t, ctl.etcdAddr, key); err != nil || got != `{"id":"r1"}` {
		t.Fatalf("store must survive restart, got: %q, err: %v", got, err)
	}

	if code := doControl(t, mux, http.MethodDelete, controlEtcdKVPath+"?key="+key, ""); code != 204 {
		t.Fatalf("delete status: %d", code)
	}
	if got, err := etcdGet(t, ctl.etcdAddr, key); err != nil || got != "" {
		t.Fatalf("get after delete: %q, err: %v", got, err)
	}
}

func TestDepControlRejectsBadRequests(t *testing.T) {
	ctl := newDepControl(freeLoopbackAddr(t), freeLoopbackAddr(t))
	mux := http.NewServeMux()
	ctl.registerControlHandlers(mux)

	cases := []struct {
		method string
		target string
		want   int
	}{
		{http.MethodPut, controlEtcdKVPath, http.StatusBadRequest},
		{http.MethodGet, controlEtcdKVPath + "?key=/k", http.StatusMethodNotAllowed},
		{http.MethodGet, controlEtcdStopPath, http.StatusMethodNotAllowed},
		{http.MethodGet, controlMySQLStartPath, http.StatusMethodNotAllowed},
	}
	for _, tc := range cases {
		if code := doControl(t, mux, tc.method, tc.target, ""); code != tc.want {
			t.Fatalf("%s %s status: %d, want: %d", tc.method, tc.target, code, tc.want)
		}
	}
}

func TestDepControlMySQLStopClosesConnections(t *testing.T) {
	ctl := newDepControl(freeLoopbackAddr(t), freeLoopbackAddr(t))
	defer ctl.stopAll()
	if err := ctl.startMySQL(); err != nil {
		t.Fatalf("start mysql failed, errmsg: %s", err)
	}

	conn, err := net.DialTimeout("tcp", ctl.mysqlAddr, time.Second)
	if err != nil {
		t.Fatalf("dial failed, errmsg: %s", err)
	}
	defer conn.Close()
	if _, _, err := readMySQLPacket(conn); err != nil {
		t.Fatalf("read handshake failed, errmsg: %s", err)
	}

	ctl.stopMySQL()
	_ = conn.SetReadDeadline(time.Now().Add(time.Second))
	if _, err := conn.Read(make([]byte, 1)); err == nil {
		t.Fatal("connection should be closed after mysql stop")
	}
	if _, err := net.DialTimeout("tcp", ctl.mysqlAddr, 200*time.Millisecond); err == nil {
		t.Fatal("dial should fail after mysql stop")
	}

	if err := ctl.startMySQL(); err != nil {
		t.Fatalf("restart mysql failed, errmsg: %s", err)
	}
	again, err := net.DialTimeout("tcp", ctl.mysqlAddr, time.Second)
	if err != nil {
		t.Fatalf("dial after restart failed, errmsg: %s", err)
	}
	_ = again.Close()
}
