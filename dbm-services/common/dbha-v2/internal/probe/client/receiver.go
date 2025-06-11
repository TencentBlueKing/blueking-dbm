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
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"
	"math/rand"
	"sync"
	"time"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
	"google.golang.org/grpc/connectivity"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"
)

type ReceiverClient struct {
	conn                 *grpc.ClientConn
	client               proto.ReceiverServiceClient
	stream               proto.ReceiverService_PushDataClient
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

func NewReceiverClient(ctx context.Context, endpoints string, clientId string) (*ReceiverClient, error) {
	kacp := keepalive.ClientParameters{
		Time:                constant.DefaultClientPingTime,
		Timeout:             constant.DefaultPingTimeout,
		PermitWithoutStream: true,
	}

	conn, err := grpc.NewClient(endpoints,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(kacp),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(constant.DefaultMaxReceiveMessageSize),
			grpc.MaxCallSendMsgSize(constant.DefaultMaxSendMessageSize),
		),
	)

	if err != nil {
		logger.Error("failed to new grpc client. errmsg(%v)", err)
		return nil, gerrors.New(gerrors.ComponentFailure, err.Error())
	}

	ctxBase, cancel := context.WithCancel(ctx)

	r := &ReceiverClient{
		conn:                 conn,
		client:               proto.NewReceiverServiceClient(conn),
		ctx:                  ctxBase,
		cancel:               cancel,
		reconnectInterval:    constant.DefaultClientReconnectInterval,
		maxReconnectAttempts: constant.DefaultClientMaxReconnectAttempts,
	}

	return r, nil
}

func (r *ReceiverClient) connect() error {
	r.mutex.Lock()
	if r.closed {
		r.mutex.Unlock()
		return gerrors.New(gerrors.Failure, "the grpc client is closed")
	}
	r.mutex.Unlock()

	stream, err := r.client.PushData(r.ctx)
	if err != nil {
		return gerrors.New(gerrors.Failure, err.Error())
	}

	r.mutex.Lock()
	r.stream = stream
	r.reconnectAttempts = 0
	r.mutex.Unlock()

	r.wg.Add(1)
	go r.monitorConnection()

	return nil
}

func (r *ReceiverClient) handleDisconnect() {
	defer r.wg.Done()

	r.mutex.Lock()
	if r.closed || r.reconnecting {
		r.mutex.Unlock()
		return
	}

	r.reconnecting = true
	r.mutex.Unlock()

	defer func() {
		r.mutex.Lock()
		r.reconnecting = false
		r.mutex.Unlock()
	}()

	r.mutex.Lock()
	r.reconnectAttempts++
	reconnectAttempts := r.reconnectAttempts
	maxAttempts := r.maxReconnectAttempts
	r.mutex.Unlock()

	if maxAttempts > 0 && reconnectAttempts > maxAttempts {
		logger.Warn("max reconnect attempts(%d) reached, giving up.", maxAttempts)
		return
	}

	// THe exponential backoff algorithm calculates the reconnection interval.
	backoffInterval := r.reconnectInterval * time.Duration(1<<uint(reconnectAttempts-1))
	// Add some randomness to avoid the stampede effect.
	backoffInterval = backoffInterval + time.Duration(rand.Int63n(int64(backoffInterval/2)))
	logger.Info("reconnect attempt(%d) in (%d)", reconnectAttempts, backoffInterval)
	time.Sleep(backoffInterval)

	// retry
	logger.Info("receiver client attempting to reconnect...")
	err := r.connect()
	if err != nil {
		logger.Warn("receiver client reconnect failed. errmsg(%v)", err)
		r.wg.Add(1)
		go r.handleDisconnect()
		return
	}

	logger.Info("receiver client reconnect successful")
}

func (r *ReceiverClient) getConnectionState() connectivity.State {
	r.mutex.RLocker()
	defer r.mutex.RUnlock()

	if r.conn == nil {
		return connectivity.Shutdown
	}

	return r.conn.GetState()
}

func (r *ReceiverClient) monitorConnection() {
	defer r.wg.Done()

	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-r.ctx.Done():
			return

		case <-ticker.C:
			r.mutex.RLocker()
			if r.closed {
				r.mutex.RUnlock()
				return
			}
			r.mutex.RUnlock()

			state := r.getConnectionState()
			if state == connectivity.TransientFailure || state == connectivity.Shutdown {
				logger.Warn("connection state(%s), starting reconnectiong", state.String())
				r.wg.Add(1)
				go r.handleDisconnect()
				return
			}
		}
	}
}

func (r *ReceiverClient) register() {
	msg := &proto.ReceiverRequest{}

	r.mutex.RLock()
	defer r.mutex.Unlock()

	if r.stream == nil {
		logger.Warn("receiver stream is invalid(nil)")
		return
	}

	if err := r.stream.Send(msg); err != nil {
		logger.Error("receiver client register failed. errmsg(%v)", err)
	}
}

func (r *ReceiverClient) SendMessage(content []byte) error {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	if r.closed {
		return gerrors.New(gerrors.Failure, "client is closed")
	}

	if r.stream == nil {
		return gerrors.New(gerrors.Failure, "stream is invalid(nil)")
	}

	msg := &proto.ReceiverRequest{}

	return r.stream.Send(msg)
}

func (r *ReceiverClient) Run() error {
	err := r.connect()
	if err != nil {
		logger.Error("failed to connect the remote server. errmsg(%v)", err)
		return err
	}

	return nil
}

func (r *ReceiverClient) Close() {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	if r.closed {
		return
	}
	r.closed = true

	if r.cancel != nil {
		r.cancel()
		r.cancel = nil
	}

	if r.conn != nil {
		r.conn.Close()
		r.conn = nil
	}
}
