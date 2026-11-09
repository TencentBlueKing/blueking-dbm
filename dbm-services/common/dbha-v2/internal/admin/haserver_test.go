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
	"context"
	"encoding/json"
	"errors"
	"reflect"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/api/open/serializer"
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/slot"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"gorm.io/gorm"
)

const rawDiscoveryErrText = "dial tcp 127.0.0.1:2379: connect: connection refused"

type fakeHaServerLister struct {
	list  *discovery.HaServerList
	err   error
	calls int
}

func (f *fakeHaServerLister) List(context.Context) (*discovery.HaServerList, error) {
	f.calls++
	return f.list, f.err
}

func sampleHaServers() *discovery.HaServerList {
	start := time.Date(2026, 11, 4, 6, 0, 0, 0, time.UTC)
	return &discovery.HaServerList{
		Servers: []discovery.HaServer{
			{Role: "admin", ID: "admin-1", IPs: []string{"127.0.0.1"}, StartTime: start,
				UpdatedAt: start.Add(30 * time.Minute), Uptime: "30 minutes"},
			{Role: "receiver", ID: "receiver-1", IPs: []string{"127.0.0.1", "::1"}, StartTime: start,
				UpdatedAt: start.Add(time.Minute), Uptime: "1 minute"},
		},
		IPs: []string{"127.0.0.1", "::1"},
	}
}

// presetSlot returns a slot holding value, or an empty slot when value is nil.
func presetSlot[T any](t *testing.T, name string, value *T) *slot.Slot[T] {
	t.Helper()
	s := slot.New(slot.Spec[T]{
		Name:        name,
		Fingerprint: func(config.Configuration) any { return name },
		Build:       func(context.Context, config.Configuration) (*T, error) { return value, nil },
	})
	if value != nil {
		if err := s.Rebuild(context.Background(), config.Configuration{}); err != nil {
			t.Fatalf("preset slot failed, errmsg: %s", err)
		}
	}

	return s
}

func newHaServerTestService(t *testing.T, storageAvailable bool, discoveryRes *discoveryResource) *Service {
	t.Helper()
	var storage *storageResource
	if storageAvailable {
		storage = newStorageResource(hamysql.WithGormDB(&gorm.DB{}, func() {}))
	}

	return &Service{
		storageSlot:   presetSlot(t, "storage", storage),
		discoverySlot: presetSlot(t, "discovery", discoveryRes),
	}
}

func callThroughStorageInterceptor(
	t *testing.T, g *AdminGrpcService, fullMethod string, req any, h grpc.UnaryHandler,
) (any, error) {
	t.Helper()
	return g.storageUnaryInterceptor()(context.Background(), req, &grpc.UnaryServerInfo{FullMethod: fullMethod}, h)
}

func listHaServersHandler(g *AdminGrpcService) grpc.UnaryHandler {
	return func(ctx context.Context, req any) (any, error) {
		r, _ := req.(*proto.ListHaServersRequest)
		return g.ListHaServers(ctx, r)
	}
}

func assertFailResponse(t *testing.T, resp *proto.ListHaServersResponse, err error) {
	t.Helper()
	if status.Code(err) != codes.OK {
		t.Fatalf("grpc status: %s, want OK", status.Code(err))
	}
	if resp.GetCode() != proto.HaServerListCode_HA_SERVER_LIST_FAIL ||
		resp.GetErrmsg() != serializer.HaServerListUnavailableMessage ||
		resp.Servers == nil || len(resp.Servers) != 0 || resp.Ips == nil || len(resp.Ips) != 0 {
		t.Fatalf("fail response: %+v", resp)
	}
}

func TestListHaServersResponseMatchesHTTP(t *testing.T) {
	data := serializer.NewHaServerListData(sampleHaServers())
	resp := newListHaServersResponse(data)

	encoded, err := json.Marshal(data)
	if err != nil {
		t.Fatalf("marshal failed, errmsg: %s", err)
	}
	var httpData struct {
		Servers []map[string]any `json:"servers"`
		IPs     []string         `json:"ips"`
	}
	if err := json.Unmarshal(encoded, &httpData); err != nil {
		t.Fatalf("unmarshal failed, errmsg: %s", err)
	}

	if !reflect.DeepEqual(resp.GetIps(), httpData.IPs) || len(resp.GetServers()) != len(httpData.Servers) {
		t.Fatalf("C05 ips or count differ, grpc: %+v, http: %s", resp, encoded)
	}
	for i, s := range resp.GetServers() {
		h := httpData.Servers[i]
		ips := make([]string, 0)
		for _, ip := range h["ips"].([]any) {
			ips = append(ips, ip.(string))
		}
		if s.GetRole() != h["role"] || s.GetId() != h["id"] || !reflect.DeepEqual(s.GetIps(), ips) ||
			s.GetStartTime() != h["start_time"] || s.GetUpdatedAt() != h["updated_at"] || s.GetUptime() != h["uptime"] {
			t.Fatalf("C05 server[%d] differs, grpc: %+v, http: %v", i, s, h)
		}
	}

	if resp.GetServers()[0].GetStartTime() != "2026-11-04T14:00:00+08:00" {
		t.Fatalf("C01 grpc start time: %s", resp.GetServers()[0].GetStartTime())
	}
}

func TestListHaServersEmptyResponse(t *testing.T) {
	resp := newListHaServersResponse(serializer.NewHaServerListData(nil))
	if resp.GetCode() != proto.HaServerListCode_HA_SERVER_LIST_SUCCESS || resp.GetErrmsg() != "success" ||
		len(resp.GetServers()) != 0 || len(resp.GetIps()) != 0 {
		t.Fatalf("C06 G02 empty response: %+v", resp)
	}
}

func TestListHaServersGRPCSuccess(t *testing.T) {
	for _, storageAvailable := range []bool{true, false} {
		srv := newHaServerTestService(t, storageAvailable, nil)
		g := &AdminGrpcService{srv: srv, haServers: &fakeHaServerLister{list: sampleHaServers()}}

		for _, req := range []*proto.ListHaServersRequest{{}, nil} {
			reply, err := callThroughStorageInterceptor(t, g, proto.AdminService_ListHaServers_FullMethodName,
				req, listHaServersHandler(g))
			if err != nil {
				t.Fatalf("G01 G05 G07 storage: %v, errmsg: %s", storageAvailable, err)
			}

			resp := reply.(*proto.ListHaServersResponse)
			want := newListHaServersResponse(serializer.NewHaServerListData(sampleHaServers()))
			if resp.GetCode() != proto.HaServerListCode_HA_SERVER_LIST_SUCCESS || resp.GetErrmsg() != "success" ||
				!reflect.DeepEqual(resp.GetIps(), want.GetIps()) || len(resp.GetServers()) != 2 ||
				resp.GetServers()[1].GetId() != "receiver-1" {
				t.Fatalf("G01 storage: %v, resp: %+v", storageAvailable, resp)
			}
		}
	}
}

func installHaServerWarnCapture(t *testing.T) *warnCaptureLogger {
	t.Helper()
	prev := logger.Log()
	capture := &warnCaptureLogger{}
	logger.SetLogger(capture)
	t.Cleanup(func() { logger.SetLogger(prev) })

	return capture
}

func assertSingleWarn(t *testing.T, capture *warnCaptureLogger, want string) {
	t.Helper()
	if logs := capture.warnMessages(); len(logs) != 1 || logs[0] != want {
		t.Fatalf("warn logs: %q, want exactly: %q", logs, want)
	}
}

func TestListHaServersGRPCFailure(t *testing.T) {
	t.Run("G03 discovery read error", func(t *testing.T) {
		capture := installHaServerWarnCapture(t)
		g := &AdminGrpcService{
			srv:       newHaServerTestService(t, false, nil),
			haServers: &fakeHaServerLister{err: errors.New(rawDiscoveryErrText)},
		}
		resp, err := g.ListHaServers(context.Background(), &proto.ListHaServersRequest{})
		assertFailResponse(t, resp, err)
		assertSingleWarn(t, capture, "list ha servers failed, errmsg: "+rawDiscoveryErrText)
	})

	t.Run("G04 discovery slot empty", func(t *testing.T) {
		capture := installHaServerWarnCapture(t)
		srv := newHaServerTestService(t, true, nil)
		g := NewAdminGrpcService(srv)
		resp, err := g.ListHaServers(context.Background(), &proto.ListHaServersRequest{})
		assertFailResponse(t, resp, err)
		assertSingleWarn(t, capture, "list ha servers failed, errmsg: "+errDiscoveryUnavailable.Error())
	})

	t.Run("G03 real discovery unreachable", func(t *testing.T) {
		client, err := discovery.NewClientWithOptions(discovery.OptionEndpoints([]string{freeGRPCAddress(t)}))
		if err != nil {
			t.Fatalf("create client failed, errmsg: %s", err)
		}
		reader, _ := client.CreateDiscovery()
		defer reader.Close()

		srv := newHaServerTestService(t, true, &discoveryResource{discovery: reader})
		g := NewAdminGrpcService(srv)
		ctx, cancel := context.WithTimeout(context.Background(), 300*time.Millisecond)
		defer cancel()
		resp, err := g.ListHaServers(ctx, &proto.ListHaServersRequest{})
		assertFailResponse(t, resp, err)
	})
}

func TestStorageInterceptorUnchangedForExistingRPCs(t *testing.T) {
	srv := newHaServerTestService(t, false, nil)
	g := NewAdminGrpcService(srv)
	called := false
	h := func(context.Context, any) (any, error) {
		called = true
		return nil, nil
	}

	for _, method := range []string{
		proto.AdminService_GetProbeConfig_FullMethodName,
		proto.AdminService_Heartbeat_FullMethodName,
		"/AdminService/ListHaServersX",
	} {
		_, err := callThroughStorageInterceptor(t, g, method, &proto.HeartbeatRequest{}, h)
		if status.Code(err) != codes.Unavailable || called {
			t.Fatalf("G06 method: %s, err: %v, handler called: %v", method, err, called)
		}
	}
}
