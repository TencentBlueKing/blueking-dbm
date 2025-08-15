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

package probe

import (
	"context"
	"io"
	"net"
	"strings"
	"sync"

	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/peer"
)

type Probe struct {
	proto.UnimplementedReceiverServiceServer
	wg     sync.WaitGroup
	savers []sink.Outputter
	cfg    config.IntputConfig
	svr    *grpc.Server
}

// NewProbeServer new a receiver server
func NewProbeServer(cfg config.IntputConfig, outputers []sink.Outputter) (*Probe, error) {
	addr := strings.TrimSpace(cfg.Endpoints)
	if addr == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "address is required")
	}

	return &Probe{cfg: cfg, savers: outputers}, nil
}

func (p *Probe) PushData(stream proto.ReceiverService_PushDataServer) error {
	ctx := stream.Context()
	addr, ok := peer.FromContext(ctx)

	clientId := ""
	if ok {
		clientId = addr.Addr.String()
	}

	connHandler := &connectionHandler{savers: p.savers}
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
				logger.Error("receiver server exited. recv return errmsg(%v)", err)
				return nil
			}

			if err != nil {
				logger.Error("receiver server exited. recv return errmsg(%v)", err)
				return nil
			}

			if err := connHandler.postEvent(req); err != nil {
				logger.Warn("handle the client event data failed, client(%s), errmsg(%v)", clientId, err)
			}
		}
	}
}

func (p *Probe) Run(ctx context.Context) error {
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

	proto.RegisterReceiverServiceServer(svr, p)
	listen, err := net.Listen("tcp", p.cfg.Endpoints)
	if err != nil {
		logger.Error("receiver listen failed. address(%s)", p.cfg.Endpoints)
		return gerrors.New(gerrors.NetException, err.Error())
	}

	p.svr = svr

	return p.svr.Serve(listen)
}

func (p *Probe) Close() {
	if p.svr == nil {
		return
	}

	p.svr.Stop()
	p.wg.Wait()
}
