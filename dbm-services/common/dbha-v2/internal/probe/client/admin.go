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
	"sync"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
)

// AdminClient is the gRPC client for the admin service, used by probe to report heartbeat and fetch config.
type AdminClient struct {
	conn     *grpc.ClientConn
	client   proto.AdminServiceClient
	ctx      context.Context
	cancel   context.CancelFunc
	clientId string
	closed   bool
	mutex    sync.RWMutex
}

// NewAdminClient creates an AdminClient connected to the given admin endpoint.
func NewAdminClient(ctx context.Context, endpoint string, clientId string) (*AdminClient, error) {
	// Snapshot rather than Cfg: periodic config sync creates clients from a background
	// goroutine, which would otherwise race with hot-reload writes to the global.
	clientCfg := config.Snapshot().Client

	pingTime := clientCfg.PingTime
	if pingTime == 0 {
		pingTime = constant.DefaultClientPingTime
	}
	pingTimeout := clientCfg.PingTimeout
	if pingTimeout == 0 {
		pingTimeout = constant.DefaultPingTimeout
	}
	maxRecvMsgSize := clientCfg.MaxReceiveMessageSize
	if maxRecvMsgSize == 0 {
		maxRecvMsgSize = constant.DefaultMaxReceiveMessageSize
	}
	maxSendMsgSize := clientCfg.MaxSendMessageSize
	if maxSendMsgSize == 0 {
		maxSendMsgSize = constant.DefaultMaxSendMessageSize
	}

	kacp := keepalive.ClientParameters{
		Time:                pingTime,
		Timeout:             pingTimeout,
		PermitWithoutStream: true,
	}

	conn, err := grpc.NewClient(endpoint,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(kacp),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(maxRecvMsgSize),
			grpc.MaxCallSendMsgSize(maxSendMsgSize),
		),
	)

	if err != nil {
		logger.Error("create admin grpc client failed, errmsg: %s", err)
		return nil, gerrors.New(gerrors.GrpcFailure, err.Error())
	}

	ctxBase, cancel := context.WithCancel(ctx)

	r := &AdminClient{
		conn:     conn,
		client:   proto.NewAdminServiceClient(conn),
		ctx:      ctxBase,
		cancel:   cancel,
		clientId: clientId,
	}

	return r, nil
}

// HeartbeatRequest sends heartbeat to admin.
func (a *AdminClient) HeartbeatRequest(req *proto.HeartbeatRequest) (*proto.HeartbeatResponse, error) {
	a.mutex.RLock()
	defer a.mutex.RUnlock()

	if a.closed {
		return nil, gerrors.New(gerrors.GrpcFailure, "admin client connection broken")
	}

	return a.client.Heartbeat(a.ctx, req)
}

// GetProbeConfig fetches probe config from admin.
func (a *AdminClient) GetProbeConfig(
	ctx context.Context, req *proto.ProbeConfigRequest,
) (*proto.ProbeConfigResponse, error) {
	a.mutex.RLock()
	defer a.mutex.RUnlock()

	if a.closed {
		return nil, gerrors.New(gerrors.GrpcFailure, "admin client is closed")
	}

	return a.client.GetProbeConfig(ctx, req)
}

// Close closes the admin client and connection.
func (a *AdminClient) Close() {
	a.mutex.Lock()
	if a.closed {
		a.mutex.Unlock()
		return
	}
	a.closed = true
	a.mutex.Unlock()

	if a.conn != nil {
		a.conn.Close()
		a.conn = nil
	}

	if a.cancel != nil {
		a.cancel()
		a.cancel = nil
	}
}
