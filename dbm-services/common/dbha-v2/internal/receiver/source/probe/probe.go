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
	"net"
	"sync"

	"dbm-services/common/dbha-v2/internal/receiver/apm"
	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
)

const Name = "probe"

// Probe is a gRPC receiver server that accepts probe data streams and dispatches them to configured sinkers.
type Probe struct {
	proto.UnimplementedReceiverServiceServer
	wg          sync.WaitGroup
	savers      []sink.Sinker
	cfg         config.SourceConfig
	ep          *hanet.Endpoint
	svr         *grpc.Server
	connHandler *connectionHandler
}

// NewProbeServer creates a new receiver server. The endpoint is parsed and validated once here;
// Run reuses the cached result to avoid redundant parsing.
func NewProbeServer(cfg config.SourceConfig) (*Probe, error) {
	ep, err := hanet.Parse(cfg.Endpoints, "tcp")
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid probe source endpoint, errmsg: %s", err)
	}

	return &Probe{
		cfg:         cfg,
		ep:          ep,
		connHandler: &connectionHandler{bufferSize: cfg.BufferSize},
	}, nil
}

// Run starts the gRPC server and blocks until Serve returns or the listener fails.
func (p *Probe) Run(ctx context.Context) error {
	serverPingTime := p.cfg.GrpcServerPingTime
	if serverPingTime <= 0 {
		serverPingTime = constant.DefaultServerPingTime
	}
	pingTimeout := p.cfg.GrpcPingTimeout
	if pingTimeout <= 0 {
		pingTimeout = constant.DefaultPingTimeout
	}
	keepAliveMinTime := p.cfg.GrpcKeepAliveMinTime
	if keepAliveMinTime <= 0 {
		keepAliveMinTime = constant.DefaultKeepAliveMiniTime
	}
	maxRecvMsgSize := p.cfg.GrpcMaxReceiveMessageSize
	if maxRecvMsgSize <= 0 {
		maxRecvMsgSize = constant.DefaultMaxReceiveMessageSize
	}
	maxSendMsgSize := p.cfg.GrpcMaxSendMessageSize
	if maxSendMsgSize <= 0 {
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

func (p *Probe) PushDataUnary(ctx context.Context, req *proto.ReceiverRequest) (*proto.ReceiverResponse, error) {
	if err := apm.ProbeReceiveMessagesTotal.IncWithLabels(map[string]string{
		apm.MetricLabelProbe: "probe",
	}); err != nil {
		logger.Warn("update probe read messages metric failed, errmsg: %s", err)
	}

	dataLength := len(req.Payload)
	if err := apm.ProbeReceiveBytesTotal.AddWithLabels(map[string]string{
		apm.MetricLabelProbe: "probe",
	}, float64(dataLength)); err != nil {
		logger.Warn("update probe read bytes metric failed, errmsg: %s", err)
	}

	err := p.connHandler.postEvent(req)
	if err == nil {
		return &proto.ReceiverResponse{
			Code:   0,
			Errmsg: "success",
		}, nil
	}

	logger.Warn("postEvent failed, errmsg: %s", err)

	if metricErr := apm.ProbeQueueFullTotal.IncWithLabels(map[string]string{
		apm.MetricLabelProbe: "probe",
	}); metricErr != nil {
		logger.Warn("update probe queue full metric failed, errmsg: %s", metricErr)
	}

	return &proto.ReceiverResponse{
		Code:   1,
		Errmsg: "failed to post event to connection handler",
	}, nil
}

func (p *Probe) Harvest(ctx context.Context, savers []sink.Sinker) error {
	p.wg.Add(1)
	go func(ctx context.Context) {
		defer p.wg.Done()
		if err := p.Run(ctx); err != nil {
			logger.Error("run probe source failed, errmsg: %s", err)
		}
	}(ctx)

	p.savers, p.connHandler.savers = savers, savers
	p.connHandler.run()
	return nil
}

// Close stops the gRPC server if it was started and waits for in-flight work registered on the wait group.
func (p *Probe) Close() {
	if p.svr != nil {
		p.svr.Stop()
		p.wg.Wait()
	}

	if p.connHandler != nil {
		p.connHandler.close()
	}
}
