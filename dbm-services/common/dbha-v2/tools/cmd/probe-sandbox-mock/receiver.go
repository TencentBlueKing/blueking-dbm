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

type mockReceiverServer struct {
	proto.UnimplementedReceiverServiceServer
	st *appStats
}

func (s *mockReceiverServer) PushDataUnary(
	_ context.Context,
	req *proto.ReceiverRequest,
) (*proto.ReceiverResponse, error) {
	payload := req.GetPayload()
	s.st.recordPush(payload)
	log.Printf("receiver push, bytes: %d", len(payload))
	return &proto.ReceiverResponse{Code: 0, Errmsg: "success"}, nil
}

func startReceiver(addr string, st *appStats) (func(), error) {
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, err
	}
	grpcSvr := grpc.NewServer()
	proto.RegisterReceiverServiceServer(grpcSvr, &mockReceiverServer{st: st})
	go func() {
		_ = grpcSvr.Serve(lis)
	}()
	return func() {
		grpcSvr.GracefulStop()
		_ = lis.Close()
	}, nil
}
