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

package service

import (
	"context"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"
	"io"
	"net"
	"strings"
	"sync"

	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
)

type Admin struct {
	proto.UnimplementedAdminServiceServer
	wg      sync.WaitGroup
	address string
	svr     *grpc.Server
}

// NewAdminServer new a admin server
func NewAdminServer(address string) (*Admin, error) {
	addr := strings.TrimSpace(address)
	if addr == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "address is required")
	}

	return &Admin{
		address: addr,
	}, nil
}

func (a *Admin) Heartbeat(ctx context.Context, req *proto.HeartbeatRequest) (*proto.HeartbeatResponse, error) {
	logger.Info("admin server heartbeat request(%v)", req)
	return &proto.HeartbeatResponse{Errmsg: "success"}, nil
}

func (a *Admin) WatchConfig(stream proto.AdminService_WatchConfigServer) error {
	ctx := stream.Context()

	for {
		select {
		case <-ctx.Done():
			logger.Error("admin server exited due to canceled context")
			return nil

		default:
			req, err := stream.Recv()
			if err == io.EOF {
				logger.Error("admin server exited. recv return errmsg(%v)", err)
				return nil
			}

			if err != nil {
				logger.Error("admin server exited. recv return errmsg(%v)", err)
				return nil
			}

			logger.Debug("request:%v", req)
			// NOTE: only test
			err = stream.Send(&proto.ProbeConfigResponse{
				Payload: "config respond",
			})
			if err != nil {
				logger.Error("respond config request failed, errmsg(%v)", err)
			}
		}
	}
}

func (a *Admin) Run() error {
	kasp := keepalive.ServerParameters{
		Time:    constant.DefaultServerPingTime,
		Timeout: constant.DefaultPingTimeout,
	}

	kacp := keepalive.EnforcementPolicy{
		MinTime:             constant.DefaultKeepAliveMiniTime,
		PermitWithoutStream: true,
	}

	svr := grpc.NewServer(
		grpc.KeepaliveParams(kasp),
		grpc.KeepaliveEnforcementPolicy(kacp),
		grpc.MaxRecvMsgSize(constant.DefaultMaxReceiveMessageSize),
		grpc.MaxSendMsgSize(constant.DefaultMaxSendMessageSize),
	)

	proto.RegisterAdminServiceServer(svr, a)
	listen, err := net.Listen("tcp", a.address)
	if err != nil {
		return gerrors.New(gerrors.NetException, err.Error())
	}

	a.svr = svr
	return a.svr.Serve(listen)

}

func (a *Admin) Close() {
	if a.svr != nil {
		a.svr.Stop()
		a.svr = nil
	}

	a.wg.Wait()
}
