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

package client

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"strings"
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type fakeReceiverServer struct {
	proto.UnimplementedReceiverServiceServer
	mu       sync.Mutex
	requests []*proto.ReceiverRequest
	response *proto.ReceiverResponse
	err      error
}

func (s *fakeReceiverServer) PushDataUnary(
	ctx context.Context,
	req *proto.ReceiverRequest,
) (*proto.ReceiverResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.requests = append(s.requests, req)

	if s.err != nil {
		return s.response, s.err
	}

	if s.response != nil {
		return s.response, nil
	}

	return &proto.ReceiverResponse{
		Code:   0,
		Errmsg: "success",
	}, nil
}

func startFakeReceiverServer(
	t *testing.T,
	srv *fakeReceiverServer,
) (endpoint string, stop func()) {
	t.Helper()

	listen, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen fake receiver failed: %v", err)
	}

	grpcServer := grpc.NewServer()
	proto.RegisterReceiverServiceServer(grpcServer, srv)

	go func() {
		grpcServer.Serve(listen)
	}()

	stop = func() {
		grpcServer.Stop()
		listen.Close()
	}

	return listen.Addr().String(), stop
}

func TestReceiverClientPostSuccess(t *testing.T) {
	ctx := context.Background()
	srv := &fakeReceiverServer{
		requests: make([]*proto.ReceiverRequest, 0),
		response: &proto.ReceiverResponse{
			Code:   0,
			Errmsg: "success",
		},
	}

	endpoint, stop := startFakeReceiverServer(t, srv)
	defer stop()

	cli, err := NewReceiverClient(ctx, endpoint, "test-client")
	if err != nil {
		t.Fatalf("new receiver client failed: %v", err)
	}
	defer cli.Close()

	payload := []byte(`{"db_type":"mysql"}`)

	if err := cli.Post(ctx, payload); err != nil {
		t.Fatalf("post failed: %v", err)
	}

	if len(srv.requests) != 1 {
		t.Fatalf("server failed to get request")
	}

	if !bytes.Equal(srv.requests[0].Payload, payload) {
		t.Fatalf("payload = %s, want %s", srv.requests[0].Payload, payload)
	}
}

func TestReceiverClientPostGrpcError(t *testing.T) {
	ctx := context.Background()
	srv := &fakeReceiverServer{
		err: status.Error(codes.Internal, "fake grpc internal error"),
	}

	endpoint, stop := startFakeReceiverServer(t, srv)
	defer stop()

	cli, err := NewReceiverClient(ctx, endpoint, "test-client")
	if err != nil {
		t.Fatalf("new receiver client failed: %v", err)
	}
	defer cli.Close()

	payload := []byte(`{"db_type":"mysql"}`)

	err = cli.Post(ctx, payload)
	if err == nil {
		t.Fatal("post error = nil, want non-nil")
	}

	if !strings.Contains(err.Error(), "fake grpc internal error") {
		t.Fatalf("error = %q, want contains fake grpc internal error", err.Error())
	}
}

func TestReceiverClientPostAfterClose(t *testing.T) {
	ctx := context.Background()

	srv := &fakeReceiverServer{}
	endpoint, stop := startFakeReceiverServer(t, srv)
	defer stop()

	cli, err := NewReceiverClient(ctx, endpoint, "test-client")
	if err != nil {
		t.Fatalf("new receiver client failed: %v", err)
	}
	cli.Close()

	payload := []byte(`{"db_type":"mysql"}`)

	if err := cli.Post(ctx, payload); err == nil {
		t.Fatal("post after close error = nil, want non-nil")
	} else {
		if !strings.Contains(err.Error(), "receiver client closed") {
			t.Fatalf("error = %q, want contains receiver client closed", err.Error())
		}
	}
}

func TestReceiverClientGetBaseInfo(t *testing.T) {
	// Apply rather than assigning Cfg: GetBaseInfo reads the race-free snapshot, which only
	// tracks configurations installed through Apply.
	saved := config.Cfg
	t.Cleanup(func() {
		config.Apply(saved)
	})

	withReporter := saved
	withReporter.Reporter = &config.ReporterConfig{BkCloudID: 123}
	config.Apply(withReporter)

	srv := &fakeReceiverServer{}
	endpoint, stop := startFakeReceiverServer(t, srv)
	defer stop()

	cli, err := NewReceiverClient(context.Background(), endpoint, "test-client")
	if err != nil {
		t.Fatalf("new receiver client failed: %v", err)
	}
	defer cli.Close()

	baseInfo := cli.GetBaseInfo()
	if baseInfo.AgentID != "" {
		t.Fatalf("AgentID = %q, want empty", baseInfo.AgentID)
	}
	if baseInfo.BkCloudID != 123 {
		t.Fatalf("BkCloudID = %d, want 123", baseInfo.BkCloudID)
	}
}

func TestNewReporterCase(t *testing.T) {
	saved := config.Cfg
	t.Cleanup(func() {
		config.Apply(saved)
	})

	srv := &fakeReceiverServer{}
	endpoint, stop := startFakeReceiverServer(t, srv)
	defer stop()

	next := saved
	next.Reporter = &config.ReporterConfig{Name: "GRPC", Endpoint: endpoint}
	config.Apply(next)

	reporter, err := NewReporter(*config.Snapshot().Reporter)
	if err != nil {
		t.Fatalf("failed to create new reporter: %v", err)
	}
	defer reporter.Close()

	if reporter.Name() != "GRPC" {
		t.Fatalf("wrong reporter, want GRPC, got %s", reporter.Name())
	}
}

func TestPostWithDisconnectedClient(t *testing.T) {
	ctx := context.Background()
	endpoint := "127.0.0.1:19999"

	cli, err := NewReceiverClient(ctx, endpoint, "test-client")
	if err != nil {
		t.Fatalf("new receiver client failed: %v", err)
	}
	defer cli.Close()

	payload := []byte(`{"db_type":"mysql"}`)

	postErr := cli.Post(ctx, payload)
	if postErr == nil {
		t.Fatal("expect a grpc error, got nil")
	}
	logger.Infof("failed to push data, errmsg: %v", postErr)
}

func TestRoundRobinBalancing(t *testing.T) {
	ctx := context.Background()

	srv1 := &fakeReceiverServer{}
	srv2 := &fakeReceiverServer{}

	addr1, stop1 := startFakeReceiverServer(t, srv1)
	defer stop1()
	addr2, stop2 := startFakeReceiverServer(t, srv2)
	defer stop2()

	endpoint := addr1 + ";" + addr2
	cli, err := NewReceiverClient(ctx, endpoint, "test-client")
	if err != nil {
		t.Fatalf("new receiver client failed: %v", err)
	}
	defer cli.Close()

	payload := []byte(`{"db_type":"mysql"}`)
	total := 100

	if err := waitUntilReady(t, cli, payload, 3*time.Second); err != nil {
		t.Fatalf("client did not become ready: %v", err)
	}

	srv1.mu.Lock()
	srv1.requests = srv1.requests[:0]
	srv1.mu.Unlock()
	srv2.mu.Lock()
	srv2.requests = srv2.requests[:0]
	srv2.mu.Unlock()

	for i := range total {
		if err := cli.Post(ctx, payload); err != nil {
			t.Fatalf("post[%d] failed: %v", i, err)
		}
	}

	srv1.mu.Lock()
	count1 := len(srv1.requests)
	srv1.mu.Unlock()
	srv2.mu.Lock()
	count2 := len(srv2.requests)
	srv2.mu.Unlock()

	if count1+count2 != total {
		t.Fatalf("total received = %d, want %d", count1+count2, total)
	}

	tolerance := 2
	diff := count1 - count2
	if diff < 0 {
		diff = -diff
	}
	if diff > tolerance {
		t.Fatalf("uneven distribution: srv1=%d srv2=%d (diff=%d, tolerance=%d)",
			count1, count2, diff, tolerance)
	}
	t.Logf("round_robin distribution: srv1=%d srv2=%d (total=%d)", count1, count2, count1+count2)
}

func TestFailoverToHealthyReceiver(t *testing.T) {
	ctx := context.Background()

	srv := &fakeReceiverServer{}
	addr, stop := startFakeReceiverServer(t, srv)
	defer stop()

	deadAddr := unusedLocalAddr(t)

	endpoint := deadAddr + ";" + addr
	cli, err := NewReceiverClient(ctx, endpoint, "test-client")
	if err != nil {
		t.Fatalf("new receiver client failed: %v", err)
	}
	defer cli.Close()

	payload := []byte(`{"db_type":"mysql"}`)
	total := 20

	if err := waitUntilReady(t, cli, payload, 5*time.Second); err != nil {
		t.Fatalf("client did not become ready: %v", err)
	}

	srv.mu.Lock()
	srv.requests = srv.requests[:0]
	srv.mu.Unlock()

	for i := range total {
		if err := cli.Post(ctx, payload); err != nil {
			t.Fatalf("post[%d] failed: %v", i, err)
		}
	}

	srv.mu.Lock()
	count := len(srv.requests)
	srv.mu.Unlock()

	if count != total {
		t.Fatalf("healthy receiver got %d requests, want %d", count, total)
	}
	t.Logf("failover ok: all %d requests routed to healthy receiver", count)
}

func waitUntilReady(t *testing.T, cli *ReceiverClient, payload []byte, timeout time.Duration) error {
	t.Helper()
	deadline := time.Now().Add(timeout)
	ctx := context.Background()
	for time.Now().Before(deadline) {
		if err := cli.Post(ctx, payload); err == nil {
			return nil
		}
		time.Sleep(100 * time.Millisecond)
	}
	return fmt.Errorf("client not ready after %s", timeout)
}

func unusedLocalAddr(t *testing.T) string {
	t.Helper()
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("failed to find unused port: %v", err)
	}
	addr := l.Addr().String()
	l.Close()
	return addr
}
