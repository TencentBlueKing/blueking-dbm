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
	"log"
	"net"

	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
)

type mockAdminServer struct {
	proto.UnimplementedAdminServiceServer
	st  *appStats
	ctl *adminControl
}

func (s *mockAdminServer) Heartbeat(
	_ context.Context,
	req *proto.HeartbeatRequest,
) (*proto.HeartbeatResponse, error) {
	s.st.incHeartbeat()
	log.Printf("admin heartbeat, client_id: %s", req.GetClientID())
	return &proto.HeartbeatResponse{Code: 0, Errmsg: "ok"}, nil
}

func (s *mockAdminServer) GetProbeConfig(
	_ context.Context,
	req *proto.ProbeConfigRequest,
) (*proto.ProbeConfigResponse, error) {
	s.st.incGetProbeConfig()
	s.ctl.recordRequest(req)
	log.Printf(
		"admin get probe config, bk_cloud_id: %d, ip: %s, client_id: %s",
		req.GetBkCloudId(), req.GetIp(), req.GetClientID(),
	)
	return s.ctl.respond(), nil
}

func startAdmin(addr string, st *appStats, ctl *adminControl) (func(), error) {
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, err
	}
	grpcSvr := grpc.NewServer()
	proto.RegisterAdminServiceServer(grpcSvr, &mockAdminServer{st: st, ctl: ctl})
	go func() {
		_ = grpcSvr.Serve(lis)
	}()
	return func() {
		grpcSvr.GracefulStop()
		_ = lis.Close()
	}, nil
}
