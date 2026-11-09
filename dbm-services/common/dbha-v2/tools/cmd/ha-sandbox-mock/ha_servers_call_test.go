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
	"errors"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
)

const (
	sampleHTTPSuccess = `{"data":{"servers":[{"role":"admin","id":"a1","ips":["127.0.0.1"],` +
		`"start_time":"2026-11-04T14:00:00+08:00","updated_at":"2026-11-04T14:30:00+08:00",` +
		`"uptime":"30 minutes"}],"ips":["127.0.0.1"]},"code":0,"message":""}`
	sampleHTTPFailure = `{"data":"","code":1,"message":"service discovery unavailable"}`
)

type stubHaServersGRPC struct {
	proto.UnimplementedAdminServiceServer
	resp *proto.ListHaServersResponse
}

func (s *stubHaServersGRPC) ListHaServers(
	context.Context, *proto.ListHaServersRequest,
) (*proto.ListHaServersResponse, error) {
	return s.resp, nil
}

func sampleGRPCSuccess(uptime string) *proto.ListHaServersResponse {
	return &proto.ListHaServersResponse{
		Code:   proto.HaServerListCode_HA_SERVER_LIST_SUCCESS,
		Errmsg: "success",
		Servers: []*proto.HaServerInfo{{
			Role: "admin", Id: "a1", Ips: []string{"127.0.0.1"},
			StartTime: "2026-11-04T14:00:00+08:00", UpdatedAt: "2026-11-04T14:30:00+08:00", Uptime: uptime,
		}},
		Ips: []string{"127.0.0.1"},
	}
}

func startStubHaServersGRPC(t *testing.T, resp *proto.ListHaServersResponse) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed, errmsg: %s", err)
	}
	srv := grpc.NewServer()
	proto.RegisterAdminServiceServer(srv, &stubHaServersGRPC{resp: resp})
	go func() { _ = srv.Serve(ln) }()
	t.Cleanup(srv.Stop)

	return ln.Addr().String()
}

func startStubHaServersHTTP(t *testing.T, status int, body string) string {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet || r.URL.Path != haServersHTTPPath {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_, _ = w.Write([]byte(body))
	}))
	t.Cleanup(srv.Close)

	return strings.TrimPrefix(srv.URL, "http://")
}

func TestCollectHaServersConsistent(t *testing.T) {
	grpcAddr := startStubHaServersGRPC(t, sampleGRPCSuccess("30 minutes"))
	webAddr := startStubHaServersHTTP(t, http.StatusOK, sampleHTTPSuccess)

	got, err := collectHaServers(grpcAddr, webAddr)
	if err != nil {
		t.Fatalf("collect failed, errmsg: %s", err)
	}
	if got.Consistent == nil || !*got.Consistent {
		t.Fatalf("want consistent, got: %+v", got)
	}
	if got.GRPC.GRPCCode != "OK" || got.GRPC.Code != "HA_SERVER_LIST_SUCCESS" || got.HTTP.Status != 200 ||
		got.HTTP.Code != 0 || len(got.HTTP.Servers) != 1 || got.HTTP.Servers[0].StartTime == "" {
		t.Fatalf("unexpected result, grpc: %+v, http: %+v", got.GRPC, got.HTTP)
	}
}

func TestCollectHaServersInconsistent(t *testing.T) {
	grpcAddr := startStubHaServersGRPC(t, sampleGRPCSuccess("31 minutes"))
	webAddr := startStubHaServersHTTP(t, http.StatusOK, sampleHTTPSuccess)

	got, err := collectHaServers(grpcAddr, webAddr)
	if err != nil {
		t.Fatalf("collect failed, errmsg: %s", err)
	}
	if got.Consistent == nil || *got.Consistent {
		t.Fatalf("want inconsistent, got: %+v", got)
	}
}

func TestCollectHaServersFailure(t *testing.T) {
	grpcAddr := startStubHaServersGRPC(t, &proto.ListHaServersResponse{
		Code: proto.HaServerListCode_HA_SERVER_LIST_FAIL, Errmsg: "service discovery unavailable",
	})
	webAddr := startStubHaServersHTTP(t, http.StatusBadRequest, sampleHTTPFailure)

	got, err := collectHaServers(grpcAddr, webAddr)
	if err != nil {
		t.Fatalf("collect failed, errmsg: %s", err)
	}
	if got.GRPC.Code != "HA_SERVER_LIST_FAIL" || got.GRPC.GRPCCode != "OK" || len(got.GRPC.Servers) != 0 {
		t.Fatalf("grpc result: %+v", got.GRPC)
	}
	if got.HTTP.Status != 400 || got.HTTP.Code != 1 || got.HTTP.Message != "service discovery unavailable" ||
		got.HTTP.RawData != `""` || got.HTTP.Servers == nil || got.HTTP.IPs == nil {
		t.Fatalf("http result: %+v", got.HTTP)
	}
}

func TestCollectHaServersNeedsTarget(t *testing.T) {
	if _, err := collectHaServers("", ""); !errors.Is(err, errNoHaServersTarget) {
		t.Fatalf("err: %v", err)
	}
}

func TestCollectHaServersSingleProtocol(t *testing.T) {
	webAddr := startStubHaServersHTTP(t, http.StatusOK, sampleHTTPSuccess)
	got, err := collectHaServers("", webAddr)
	if err != nil || got.GRPC != nil || got.HTTP == nil || got.Consistent != nil {
		t.Fatalf("got: %+v, err: %v", got, err)
	}
}
