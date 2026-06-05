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
	"time"

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

var NameGRPC = "GRPC"

// ReceiverClient is the gRPC client for the receiver service.
type ReceiverClient struct {
	conn                 *grpc.ClientConn
	client               proto.ReceiverServiceClient
	wg                   sync.WaitGroup
	ctx                  context.Context
	cancel               context.CancelFunc
	clientId             string
	closed               bool
	reconnecting         bool
	reconnectInterval    time.Duration
	maxReconnectAttempts int
	reconnectAttempts    int
	mutex                sync.RWMutex
}

// NewReceiverClient creates a ReceiverClient connected to the given endpoints.
func NewReceiverClient(ctx context.Context, endpoints string, clientId string) (*ReceiverClient, error) {
	pingTime := config.Cfg.Client.PingTime
	if pingTime <= 0 {
		pingTime = constant.DefaultClientPingTime
	}
	pingTimeout := config.Cfg.Client.PingTimeout
	if pingTimeout <= 0 {
		pingTimeout = constant.DefaultPingTimeout
	}
	maxRecvMsgSize := config.Cfg.Client.MaxReceiveMessageSize
	if maxRecvMsgSize <= 0 {
		maxRecvMsgSize = constant.DefaultMaxReceiveMessageSize
	}
	maxSendMsgSize := config.Cfg.Client.MaxSendMessageSize
	if maxSendMsgSize <= 0 {
		maxSendMsgSize = constant.DefaultMaxSendMessageSize
	}

	reconnectInterval := config.Cfg.Client.ReceiverReconnectInterval
	if reconnectInterval <= 0 {
		reconnectInterval = constant.DefaultClientReconnectInterval
	}
	maxReconnectAttempts := config.Cfg.Client.ReceiverMaxReconnectAttempts
	if maxReconnectAttempts <= 0 {
		maxReconnectAttempts = constant.DefaultClientMaxReconnectAttempts
	}

	kacp := keepalive.ClientParameters{
		Time:                pingTime,
		Timeout:             pingTimeout,
		PermitWithoutStream: true,
	}

	conn, err := grpc.NewClient(endpoints,
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
		clientId:             clientId,
		conn:                 conn,
		client:               proto.NewReceiverServiceClient(conn),
		ctx:                  ctxBase,
		cancel:               cancel,
		reconnectInterval:    reconnectInterval,
		maxReconnectAttempts: maxReconnectAttempts,
	}

	return r, nil
}

func (r *ReceiverClient) Name() string {
	return NameGRPC
}

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

func (r *ReceiverClient) GetBaseInfo() BaseInfo {
	bkCloudID := config.Cfg.Reporter.BkCloudID

	return BaseInfo{
		BkCloudID: bkCloudID,
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
