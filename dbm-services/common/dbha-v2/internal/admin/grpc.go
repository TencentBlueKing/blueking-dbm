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
	"errors"

	adminconfig "dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
)

// AdminGrpcService implements proto.AdminServiceServer.
// It is referenced by Service and its lifecycle is managed by Service.
type AdminGrpcService struct {
	proto.UnimplementedAdminServiceServer
	srv *Service
}

// NewAdminGrpcService returns a new AdminGrpcService bound to the given Service.
func NewAdminGrpcService(s *Service) *AdminGrpcService {
	return &AdminGrpcService{srv: s}
}

// NewServer creates a gRPC server with keepalive and message size options from config (defaults set in Cfg).
func (g *AdminGrpcService) NewServer() *grpc.Server {
	cfg := adminconfig.Cfg.Grpc

	kasp := keepalive.ServerParameters{
		Time:    cfg.ServerPingTime,
		Timeout: cfg.PingTimeout,
	}

	kacp := keepalive.EnforcementPolicy{
		MinTime:             cfg.KeepAliveMinTime,
		PermitWithoutStream: cfg.PermitWithoutStream,
	}

	return grpc.NewServer(
		grpc.KeepaliveParams(kasp),
		grpc.KeepaliveEnforcementPolicy(kacp),
		grpc.MaxRecvMsgSize(cfg.MaxReceiveMessageSize),
		grpc.MaxSendMsgSize(cfg.MaxSendMessageSize),
	)
}

// Heartbeat admin server heartbeat
func (g *AdminGrpcService) Heartbeat(
	ctx context.Context, req *proto.HeartbeatRequest,
) (*proto.HeartbeatResponse, error) {
	logger.Info("admin server heartbeat request(%v)", req)
	return &proto.HeartbeatResponse{Errmsg: "success"}, nil
}

// GetProbeConfig returns probe config for the given client (by cloudid + ip).
func (g *AdminGrpcService) GetProbeConfig(
	ctx context.Context, req *proto.ProbeConfigRequest,
) (*proto.ProbeConfigResponse, error) {
	logger.Debug("probe config request, bk_cloud_id: %d, ip: %s, client_id: %s, version: %s, updated_time: %d",
		req.GetBkCloudId(), req.GetIp(), req.GetClientID(), req.GetVersion(), req.GetUpdatedTime())

	payload, err := adminconfig.GenProbeConfig(ctx, g.srv.db, int(req.GetBkCloudId()), req.GetIp())
	if err != nil {
		if errors.Is(err, adminconfig.ErrNoData) {
			return &proto.ProbeConfigResponse{
				Code:    proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA,
				Errmsg:  err.Error(),
				Payload: "",
			}, nil
		}

		logger.Warn("failed to generate probe config, errmsg: %s", err)

		return &proto.ProbeConfigResponse{
			Code:    proto.ProbeConfigCode_PROBE_CONFIG_FAIL,
			Errmsg:  err.Error(),
			Payload: "",
		}, nil
	}

	return &proto.ProbeConfigResponse{
		Code:    proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS,
		Errmsg:  "success",
		Payload: payload,
	}, nil
}
