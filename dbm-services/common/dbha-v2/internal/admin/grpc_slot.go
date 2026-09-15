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
	"fmt"
	"net"
	"reflect"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/slot"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
)

type wrapListener struct {
	net.Listener
	stop chan struct{}
	once sync.Once
}

func newWrapListener(listener net.Listener) *wrapListener {
	return &wrapListener{Listener: listener, stop: make(chan struct{})}
}

func (l *wrapListener) Accept() (net.Conn, error) {
	deadlineListener, ok := l.Listener.(interface{ SetDeadline(time.Time) error })
	if !ok {
		return l.Listener.Accept()
	}
	for {
		_ = deadlineListener.SetDeadline(time.Now().Add(100 * time.Millisecond))
		connection, err := l.Listener.Accept()
		if err == nil {
			return connection, nil
		}
		select {
		case <-l.stop:
			return nil, net.ErrClosed
		default:
		}
		if netError, temporary := err.(net.Error); temporary && netError.Timeout() {
			continue
		}
		return nil, err
	}
}

func (l *wrapListener) Close() error {
	l.once.Do(func() { close(l.stop) })
	return nil
}

type grpcGeneration struct {
	server   *grpc.Server
	listener net.Listener
	done     chan struct{}
}

type grpcSlot struct {
	owner               *Service
	mu                  sync.Mutex
	current             *grpcGeneration
	fp                  config.GrpcConfig
	startGenerationHook func(net.Listener, config.GrpcConfig) (*grpcGeneration, error)
}

func newGRPCSlot(owner *Service) *grpcSlot {
	return &grpcSlot{owner: owner}
}

func (s *grpcSlot) Name() string { return "grpc" }

func (s *grpcSlot) NeedsRebuild(next config.Configuration) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.current == nil || !reflect.DeepEqual(s.fp, next.Grpc)
}

func (s *grpcSlot) Rebuild(ctx context.Context, next config.Configuration) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return err
	}
	if s.current == nil || s.fp.ListenAddress != next.Grpc.ListenAddress {
		return s.rebuildAddress(ctx, next)
	}
	return s.rebuildParameters(ctx, next)
}

func (s *grpcSlot) Close(ctx context.Context) {
	s.mu.Lock()
	defer s.mu.Unlock()
	_ = s.closeGeneration(ctx, s.current, true)
	s.current = nil
}

func (s *grpcSlot) rebuildAddress(ctx context.Context, next config.Configuration) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	listener, err := listenGRPC(next.Grpc.ListenAddress)
	if err != nil {
		return err
	}
	generation, err := s.startGeneration(listener, next.Grpc)
	if err != nil {
		_ = listener.Close()
		return err
	}
	old := s.current
	s.current = generation
	s.fp = next.Grpc
	if err := s.closeGeneration(ctx, old, true); err != nil {
		logger.Error("grpc old generation close timed out after address swap, errmsg: %s", err)
	}
	return nil
}

func (s *grpcSlot) rebuildParameters(ctx context.Context, next config.Configuration) error {
	old := s.current
	if err := s.closeGeneration(ctx, old, false); err != nil {
		return err
	}
	listener := old.listener
	generation, err := s.startGeneration(listener, next.Grpc)
	if err != nil {
		recovered, recoverErr := s.startGeneration(listener, s.fp)
		if recoverErr != nil {
			return fmt.Errorf(
				"grpc parameter rebuild failed, errmsg: %w; recover failed, errmsg: %s",
				err, recoverErr,
			)
		}
		s.current = recovered
		return fmt.Errorf(
			"grpc parameter rebuild failed after close, recovered previous config, errmsg: %w",
			err,
		)
	}
	s.current = generation
	s.fp = next.Grpc
	return nil
}

func (s *grpcSlot) startGeneration(listener net.Listener, cfg config.GrpcConfig) (*grpcGeneration, error) {
	if s.startGenerationHook != nil {
		return s.startGenerationHook(listener, cfg)
	}
	server := s.owner.grpcSvc.NewServer(cfg)
	proto.RegisterAdminServiceServer(server, s.owner.grpcSvc)
	generation := &grpcGeneration{server: server, listener: listener, done: make(chan struct{})}
	wrapped := newWrapListener(listener)
	go func() {
		defer close(generation.done)
		err := server.Serve(wrapped)
		if err != nil && !errors.Is(err, grpc.ErrServerStopped) && !s.owner.isShuttingDown() {
			logger.Error("grpc server exited unexpectedly, errmsg: %s", err)
		}
	}()
	return generation, nil
}

func (s *grpcSlot) closeGeneration(ctx context.Context, generation *grpcGeneration, closeListener bool) error {
	if generation == nil {
		return nil
	}
	if ctx == nil {
		ctx = context.Background()
	}
	timeoutCtx, cancel := context.WithTimeout(ctx, reloadSlotTimeout)
	defer cancel()

	stopDone := make(chan struct{})
	go func() {
		if generation.server != nil {
			generation.server.Stop()
		}
		if generation.done != nil {
			<-generation.done
		}
		close(stopDone)
	}()

	select {
	case <-stopDone:
		if closeListener && generation.listener != nil {
			_ = generation.listener.Close()
		}
		return nil
	case <-timeoutCtx.Done():
		logger.Error("grpc generation close timed out, errmsg: %s", timeoutCtx.Err())
		return timeoutCtx.Err()
	}
}

func listenGRPC(address string) (net.Listener, error) {
	ep, err := hanet.Parse(address, "tcp")
	if err != nil {
		return nil, gerrors.Newf(
			gerrors.InvalidConfiguration,
			"invalid admin grpc listen address, errmsg: %s",
			err,
		)
	}
	listener, err := net.Listen("tcp", ep.HostPort())
	if err != nil {
		return nil, gerrors.New(gerrors.NetException, err.Error())
	}
	return listener, nil
}

var _ slot.Ops = (*grpcSlot)(nil)
