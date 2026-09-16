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
	"testing"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
)

func TestEtcdMockGrantPutKeepAlive(t *testing.T) {
	srv, ln, err := startEtcdMock("127.0.0.1:0")
	if err != nil {
		t.Fatalf("start etcd mock failed, errmsg: %s", err)
	}
	defer srv.Stop()
	defer ln.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	cli, err := clientv3.New(clientv3.Config{
		Endpoints:   []string{ln.Addr().String()},
		DialTimeout: 3 * time.Second,
	})
	if err != nil {
		t.Fatalf("etcd client failed, errmsg: %s", err)
	}
	defer cli.Close()

	lease, err := cli.Grant(ctx, 10)
	if err != nil {
		t.Fatalf("grant failed, errmsg: %s", err)
	}
	if _, err := cli.Put(ctx, "/dbha/sandbox", "ok", clientv3.WithLease(lease.ID)); err != nil {
		t.Fatalf("put failed, errmsg: %s", err)
	}
	got, err := cli.Get(ctx, "/dbha/sandbox")
	if err != nil {
		t.Fatalf("get failed, errmsg: %s", err)
	}
	if got.Count != 1 || string(got.Kvs[0].Value) != "ok" {
		t.Fatalf("unexpected get result, count: %d", got.Count)
	}
	ch, err := cli.KeepAlive(ctx, lease.ID)
	if err != nil {
		t.Fatalf("keepalive failed, errmsg: %s", err)
	}
	select {
	case resp := <-ch:
		if resp == nil {
			t.Fatal("keepalive response is nil")
		}
	case <-ctx.Done():
		t.Fatal("keepalive timeout")
	}
}
