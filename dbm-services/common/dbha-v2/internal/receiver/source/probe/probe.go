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

// Package probe implements the gRPC receiver service that ingests probe push streams and forwards events to sinks.
package probe

import (
	"context"
	"io"
	"net"
	"sync"

	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/peer"
)

// Probe is a gRPC receiver server that accepts probe data streams and dispatches them to configured sinkers.
type Probe struct {
	proto.UnimplementedReceiverServiceServer
	wg     sync.WaitGroup
	savers []sink.Sinker
	cfg    config.SourceConfig
	ep     *hanet.Endpoint
	svr    *grpc.Server
}

// NewProbeServer creates a new receiver server. The endpoint is parsed and validated once here;
// Run reuses the cached result to avoid redundant parsing.
func NewProbeServer(cfg config.SourceConfig, outputers []sink.Sinker) (*Probe, error) {
	ep, err := hanet.Parse(cfg.Endpoints, "tcp")
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid probe source endpoint, errmsg: %s", err)
	}

	return &Probe{cfg: cfg, ep: ep, savers: outputers}, nil
}

// PushData handles a client push stream until the context is canceled, EOF,
// or a receive error; it returns nil in those cases.
func (p *Probe) PushData(stream proto.ReceiverService_PushDataServer) error {
	ctx := stream.Context()
	addr, ok := peer.FromContext(ctx)

	clientId := ""
	if ok {
		clientId = addr.Addr.String()
	}

	connHandler := &connectionHandler{
		savers:     p.savers,
		bufferSize: p.cfg.BufferSize,
	}
	connHandler.run()
	defer connHandler.close()

	for {
		select {
		case <-ctx.Done():
			logger.Error("receiver server exited due to canceled context")
			return nil

		default:
			req, err := stream.Recv()
			if err == io.EOF {
				logger.Error("receiver server exited, errmsg: %s", err)
				return nil
			}

			if err != nil {
				logger.Error("receiver server exited, errmsg: %s", err)
				return nil
			}

			if err := connHandler.postEvent(req); err != nil {
				logger.Warn("handle the client event data failed, client: %s, errmsg: %s", clientId, err)
			}
		}
	}
}

// Run starts the gRPC server and blocks until Serve returns or the listener fails.
func (p *Probe) Run(ctx context.Context) error {
	serverPingTime := p.cfg.GrpcServerPingTime
	if serverPingTime == 0 {
		serverPingTime = constant.DefaultServerPingTime
	}
	pingTimeout := p.cfg.GrpcPingTimeout
	if pingTimeout == 0 {
		pingTimeout = constant.DefaultPingTimeout
	}
	keepAliveMinTime := p.cfg.GrpcKeepAliveMinTime
	if keepAliveMinTime == 0 {
		keepAliveMinTime = constant.DefaultKeepAliveMiniTime
	}
	maxRecvMsgSize := p.cfg.GrpcMaxReceiveMessageSize
	if maxRecvMsgSize == 0 {
		maxRecvMsgSize = constant.DefaultMaxReceiveMessageSize
	}
	maxSendMsgSize := p.cfg.GrpcMaxSendMessageSize
	if maxSendMsgSize == 0 {
		maxSendMsgSize = constant.DefaultMaxSendMessageSize
	}

	kasp := keepalive.ServerParameters{
		Time:    serverPingTime,
		Timeout: pingTimeout,
	}

	kacp := keepalive.EnforcementPolicy{
		MinTime:             keepAliveMinTime,
		PermitWithoutStream: true,
	}

	svr := grpc.NewServer(
		grpc.KeepaliveParams(kasp),
		grpc.KeepaliveEnforcementPolicy(kacp),
		grpc.MaxRecvMsgSize(maxRecvMsgSize),
		grpc.MaxSendMsgSize(maxSendMsgSize),
	)

	proto.RegisterReceiverServiceServer(svr, p)

	listen, err := net.Listen("tcp", p.ep.HostPort())
	if err != nil {
		logger.Error("probe source listen failed, address: %s, errmsg: %s", p.ep.HostPort(), err)
		return gerrors.New(gerrors.NetException, err.Error())
	}

	p.svr = svr

	return p.svr.Serve(listen)
}

// Close stops the gRPC server if it was started and waits for in-flight work registered on the wait group.
func (p *Probe) Close() {
	if p.svr == nil {
		return
	}

	p.svr.Stop()
	p.wg.Wait()
}
