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

	"dbm-services/common/dbha-v2/internal/admin/api/open/handler"
	"dbm-services/common/dbha-v2/internal/admin/api/open/serializer"
	adminapm "dbm-services/common/dbha-v2/internal/admin/apm"
	adminconfig "dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/status"
)

// AdminGrpcService implements proto.AdminServiceServer.
// It is referenced by Service and its lifecycle is managed by Service.
type AdminGrpcService struct {
	proto.UnimplementedAdminServiceServer
	srv       *Service
	haServers handler.HaServerLister
}

// NewAdminGrpcService returns a new AdminGrpcService bound to the given Service.
func NewAdminGrpcService(s *Service) *AdminGrpcService {
	return &AdminGrpcService{srv: s, haServers: &haServerLister{srv: s}}
}

// NewServer creates a gRPC server with keepalive, message size, and storage lifecycle handling.
func (g *AdminGrpcService) NewServer(configs ...adminconfig.GrpcConfig) *grpc.Server {
	cfg := adminconfig.Snapshot().Grpc
	if len(configs) > 0 {
		cfg = configs[0]
	}

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
		grpc.ChainUnaryInterceptor(
			adminapm.UnaryServerInterceptor(),
			g.storageUnaryInterceptor(),
		),
	)
}

func (g *AdminGrpcService) storageUnaryInterceptor() grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req any,
		info *grpc.UnaryServerInfo,
		next grpc.UnaryHandler,
	) (any, error) {
		if info != nil && info.FullMethod == proto.AdminService_ListHaServers_FullMethodName {
			return next(ctx, req)
		}

		resource := g.srv.storageSlot.Get()
		if resource == nil || !resource.acquire() {
			return nil, status.Error(codes.Unavailable, "storage is reloading")
		}
		defer resource.release()
		return next(context.WithValue(ctx, storageContextKey{}, resource), req)
	}
}

// Heartbeat admin server heartbeat
func (g *AdminGrpcService) Heartbeat(
	_ context.Context, _ *proto.HeartbeatRequest,
) (*proto.HeartbeatResponse, error) {
	logger.Info("admin heartbeat request")
	return &proto.HeartbeatResponse{Errmsg: "success"}, nil
}

// GetProbeConfig returns probe config for the given client (by cloudid + ip).
func (g *AdminGrpcService) GetProbeConfig(
	ctx context.Context, req *proto.ProbeConfigRequest,
) (*proto.ProbeConfigResponse, error) {
	logger.Debug("probe config request, bk_cloud_id: %d, ip: %s, client_id: %s, version: %s, updated_time: %d",
		req.GetBkCloudId(), req.GetIp(), req.GetClientID(), req.GetVersion(), req.GetUpdatedTime())

	db := dbFromContext(ctx, g.srv.currentDB)
	if db == nil {
		return nil, status.Error(codes.Unavailable, "storage is unavailable")
	}
	payload, err := adminconfig.GenProbeConfig(ctx, db, int(req.GetBkCloudId()), req.GetIp())
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

// ListHaServers returns live admin, analysis and receiver instances and their merged IPs.
// It does not depend on storage. Both success and discovery failure return gRPC OK; on failure
// code is HA_SERVER_LIST_FAIL, errmsg is a fixed message and servers and ips are empty.
func (g *AdminGrpcService) ListHaServers(
	ctx context.Context, _ *proto.ListHaServersRequest,
) (*proto.ListHaServersResponse, error) {
	list, err := g.haServers.List(ctx)
	if err != nil {
		logger.Warn("list ha servers failed, errmsg: %s", err)
		return &proto.ListHaServersResponse{
			Code:    proto.HaServerListCode_HA_SERVER_LIST_FAIL,
			Errmsg:  serializer.HaServerListUnavailableMessage,
			Servers: []*proto.HaServerInfo{},
			Ips:     []string{},
		}, nil
	}

	return newListHaServersResponse(serializer.NewHaServerListData(list)), nil
}
