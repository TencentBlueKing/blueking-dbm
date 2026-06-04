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
	"net"
	"strings"
	"sync"
	"testing"

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
	oldReporter := config.Cfg.Reporter
	t.Cleanup(func() {
		config.Cfg.Reporter = oldReporter
	})

	config.Cfg.Reporter = &config.ReporterConfig{BkCloudID: 123}

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
	oldReporter := config.Cfg.Reporter
	t.Cleanup(func() {
		config.Cfg.Reporter = oldReporter
	})

	config.Cfg.Reporter = &config.ReporterConfig{Name: "GRPC"}

	reporter, err := NewReporter(*config.Cfg.Reporter)
	if err != nil {
		t.Fatalf("failed to create new reporter: %v", err)
	}

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
