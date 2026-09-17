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
	"testing"

	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
)

type stubAdminGRPC struct {
	proto.UnimplementedAdminServiceServer
}

func (s *stubAdminGRPC) Heartbeat(
	_ context.Context, _ *proto.HeartbeatRequest,
) (*proto.HeartbeatResponse, error) {
	return &proto.HeartbeatResponse{Errmsg: "success"}, nil
}

func (s *stubAdminGRPC) GetProbeConfig(
	_ context.Context, _ *proto.ProbeConfigRequest,
) (*proto.ProbeConfigResponse, error) {
	return &proto.ProbeConfigResponse{Code: proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA}, nil
}

func TestCallAdminGRPCHeartbeatAndGetProbeConfig(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed, errmsg: %s", err)
	}
	defer ln.Close()

	srv := grpc.NewServer()
	proto.RegisterAdminServiceServer(srv, &stubAdminGRPC{})
	go srv.Serve(ln)
	defer srv.Stop()

	if err := callAdminGRPC(ln.Addr().String()); err != nil {
		t.Fatalf("call admin grpc failed, errmsg: %s", err)
	}
}
