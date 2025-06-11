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

type AdminClient struct {
	conn                 *grpc.ClientConn
	client               proto.AdminServiceClient
	stream               proto.AdminService_WatchConfigClient
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

func NewAdminClient(ctx context.Context, endpoint string, clientId string) (*AdminClient, error) {
	kacp := keepalive.ClientParameters{
		Time:                constant.DefaultClientPingTime,
		Timeout:             constant.DefaultPingTimeout,
		PermitWithoutStream: true,
	}

	conn, err := grpc.NewClient(endpoint,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithKeepaliveParams(kacp),
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(constant.DefaultMaxReceiveMessageSize),
			grpc.MaxCallSendMsgSize(constant.DefaultMaxSendMessageSize),
		),
	)

	if err != nil {
		logger.Error("create admin grpc client failed. errmsg(%v)", err)
		return nil, gerrors.New(gerrors.ComponentFailure, err.Error())
	}

	ctxBase, cancel := context.WithCancel(ctx)

	r := &AdminClient{
		conn:                 conn,
		client:               proto.NewAdminServiceClient(conn),
		ctx:                  ctxBase,
		cancel:               cancel,
		reconnectInterval:    constant.DefaultClientReconnectInterval,
		maxReconnectAttempts: constant.DefaultClientMaxReconnectAttempts,
	}

	return r, nil
}

func (a *AdminClient) connect() error {
	a.mutex.Lock()
	if a.closed {
		a.mutex.Unlock()
		return gerrors.New(gerrors.Failure, "admin client is closed")
	}
	a.mutex.Unlock()

	stream, err := a.client.WatchConfig(a.ctx)
	if err != nil {
		return gerrors.New(gerrors.Failure, err.Error())
	}

	a.mutex.Lock()
	a.stream = stream
	a.reconnectAttempts = 0
	a.mutex.Unlock()

	a.wg.Add(1)
	go a.monitorConnection()

	return nil
}

func (a *AdminClient) handleDisconnect() {
	defer a.wg.Done()

	a.mutex.Unlock()
	if a.closed || a.reconnecting {
		a.mutex.Unlock()
		return
	}

	a.reconnecting = true
	a.mutex.Unlock()

	defer func() {
		a.mutex.Lock()
		a.reconnecting = false
		a.mutex.Unlock()
	}()

	a.mutex.Lock()
	a.reconnectAttempts++
	reconnectAttempts := a.reconnectAttempts
	maxAttempts := a.maxReconnectAttempts
	a.mutex.Unlock()

	if maxAttempts > 0 && reconnectAttempts > maxAttempts {
		logger.Warn("admin client max reconnect attempts(%d) reached, giving up.", maxAttempts)
		return
	}

	// THe exponential backoff algorithm calculates the reconnection interval.
	backoffInterval := a.reconnectInterval * time.Duration(1<<uint(reconnectAttempts-1))
	// Add some randomness to avoid the stampede effect.
	backoffInterval = backoffInterval + time.Duration(rand.Int63n(int64(backoffInterval/2)))
	logger.Info("reconnect attempt(%d) in (%d)", reconnectAttempts, backoffInterval)
	time.Sleep(backoffInterval)

	// retry
	logger.Info("admin client attempting to reconnect...")
	err := a.connect()
	if err != nil {
		logger.Warn("admin client reconnect failed. errmsg(%v)", err)
		a.wg.Add(1)
		go a.handleDisconnect()
		return
	}

	logger.Info("admin client reconnect successful")
}

func (a *AdminClient) getConnectionState() connectivity.State {
	a.mutex.RLock()
	defer a.mutex.RUnlock()

	if a.conn == nil {
		return connectivity.Shutdown
	}

	return a.conn.GetState()
}

func (a *AdminClient) monitorConnection() {
	defer a.wg.Done()

	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-a.ctx.Done():
			return

		case <-ticker.C:
			a.mutex.RLocker()
			if a.closed {
				a.mutex.RUnlock()
				return
			}
			a.mutex.RUnlock()

			state := a.getConnectionState()
			if state == connectivity.TransientFailure || state == connectivity.Shutdown {
				logger.Warn("connection state(%s), starting reconnectiong", state.String())
				a.wg.Add(1)
				go a.handleDisconnect()
				return
			}
		}
	}
}

func (a *AdminClient) register() {
	msg := &proto.ProbeConfigRequest{}

	a.mutex.RLock()
	defer a.mutex.Unlock()

	if a.stream == nil {
		logger.Warn("receiver stream is invalid(nil)")
		return
	}

	if err := a.stream.Send(msg); err != nil {
		logger.Error("receiver register failed. errmsg(%v)", err)
	}
}

func (a *AdminClient) SendMessage(content []byte) error {
	a.mutex.RLock()
	defer a.mutex.RUnlock()

	if a.closed {
		return gerrors.New(gerrors.Failure, "client is closed")
	}

	if a.stream == nil {
		return gerrors.New(gerrors.Failure, "stream is invalid(nil)")
	}

	msg := &proto.ProbeConfigRequest{}

	return a.stream.Send(msg)
}

func (a *AdminClient) Run() error {
	err := a.connect()
	if err != nil {
		logger.Error("admin client connect the remote server failed. errmsg(%v)", err)
		return err
	}

	return nil
}

func (a *AdminClient) Close() {
	a.mutex.Lock()
	defer a.mutex.Unlock()

	if a.closed {
		return
	}
	a.closed = true

	if a.cancel != nil {
		a.cancel()
		a.cancel = nil
	}

	if a.conn != nil {
		a.conn.Close()
		a.conn = nil
	}

	a.wg.Wait()
}
