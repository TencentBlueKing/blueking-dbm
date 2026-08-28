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
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
	"google.golang.org/grpc/resolver"
	"google.golang.org/grpc/resolver/manual"
)

var NameGRPC = "GRPC"

const (
	resolverScheme    = "dbha"
	resolverTarget    = resolverScheme + ":///receiver"
	grpcServiceConfig = `{"loadBalancingPolicy":"round_robin"}`
)

// ReceiverClient is the gRPC client for the receiver service.
type ReceiverClient struct {
	conn     *grpc.ClientConn
	client   proto.ReceiverServiceClient
	wg       sync.WaitGroup
	ctx      context.Context
	cancel   context.CancelFunc
	clientId string
	closed   bool
	mutex    sync.RWMutex
	resolver *manual.Resolver
}

// NewReceiverClient creates a ReceiverClient connected to the given endpoints.
func NewReceiverClient(ctx context.Context, endpoint string, clientId string) (*ReceiverClient, error) {
	clientCfg := config.Snapshot().Client

	pingTime := clientCfg.PingTime
	if pingTime <= 0 {
		pingTime = constant.DefaultClientPingTime
	}
	pingTimeout := clientCfg.PingTimeout
	if pingTimeout <= 0 {
		pingTimeout = constant.DefaultPingTimeout
	}
	maxRecvMsgSize := clientCfg.MaxReceiveMessageSize
	if maxRecvMsgSize <= 0 {
		maxRecvMsgSize = constant.DefaultMaxReceiveMessageSize
	}
	maxSendMsgSize := clientCfg.MaxSendMessageSize
	if maxSendMsgSize <= 0 {
		maxSendMsgSize = constant.DefaultMaxSendMessageSize
	}

	kacp := keepalive.ClientParameters{
		Time:                pingTime,
		Timeout:             pingTimeout,
		PermitWithoutStream: true,
	}

	eps, err := hanet.ParseList(endpoint, "tcp")
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid receiver endpoint(%s): %s", endpoint, err)
	}

	addrs := make([]resolver.Address, 0, len(eps))
	for _, ep := range eps {
		addrs = append(addrs, resolver.Address{Addr: ep.HostPort()})
	}

	rs := manual.NewBuilderWithScheme(resolverScheme)
	rs.InitialState(resolver.State{Addresses: addrs})

	conn, err := grpc.NewClient(resolverTarget,
		grpc.WithResolvers(rs),
		grpc.WithDefaultServiceConfig(grpcServiceConfig),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(kacp),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(maxRecvMsgSize),
			grpc.MaxCallSendMsgSize(maxSendMsgSize),
		),
	)

	if err != nil {
		logger.Error("failed to new grpc client, errmsg: %s", err)
		return nil, gerrors.New(gerrors.GrpcFailure, err.Error())
	}

	ctxBase, cancel := context.WithCancel(ctx)

	r := &ReceiverClient{
		clientId: clientId,
		conn:     conn,
		client:   proto.NewReceiverServiceClient(conn),
		resolver: rs,
		ctx:      ctxBase,
		cancel:   cancel,
	}

	return r, nil
}

// Name returns the reporter name for the gRPC receiver client.
func (r *ReceiverClient) Name() string {
	return NameGRPC
}

// Post sends content to the receiver over unary gRPC.
// It returns an error when the client is closed or the push fails.
func (r *ReceiverClient) Post(ctx context.Context, content []byte) error {
	r.mutex.Lock()
	if r.closed {
		r.mutex.Unlock()
		return gerrors.New(gerrors.GrpcFailure, "receiver client closed, failed to post messages")
	}
	r.mutex.Unlock()

	req := &proto.ReceiverRequest{
		Payload: content,
	}

	res, err := r.client.PushDataUnary(ctx, req)
	if err == nil {
		return nil
	}
	if res != nil {
		return gerrors.Newf(gerrors.GrpcFailure,
			"failed to post messages to receiver, grpc err: %s, receiver errmsg: %s",
			err, res.Errmsg)
	}
	return gerrors.New(gerrors.GrpcFailure, err.Error())
}

// GetBaseInfo returns the cloud id tagged on reported data.
// It reads the applied configuration through Snapshot so it does not race with hot reload.
// A config without a reporter block yields the zero BaseInfo, matching an unset bkCloudID.
func (r *ReceiverClient) GetBaseInfo() BaseInfo {
	reporter := config.Snapshot().Reporter
	if reporter == nil {
		return BaseInfo{}
	}

	return BaseInfo{
		BkCloudID: reporter.BkCloudID,
	}
}

// Close closes the receiver client and connection.
func (r *ReceiverClient) Close() {
	r.mutex.Lock()
	if r.closed {
		r.mutex.Unlock()
		return
	}
	r.closed = true
	r.mutex.Unlock()

	// close connection
	if r.conn != nil {
		r.conn.Close()
		r.conn = nil
	}

	// exit goroutines
	if r.cancel != nil {
		r.cancel()
		r.cancel = nil
	}

	r.wg.Wait()
}
