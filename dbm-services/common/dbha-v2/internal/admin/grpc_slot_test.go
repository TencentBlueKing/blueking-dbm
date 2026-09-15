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
	"net"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/config"
)

func TestGRPCSlotReusesListenerForParameterChange(t *testing.T) {
	service := &Service{shutdown: make(chan struct{})}
	service.grpcSvc = NewAdminGrpcService(service)
	resourceSlot := newGRPCSlot(service)
	cfg := config.Configuration{
		Grpc: config.GrpcConfig{
			ListenAddress:         freeGRPCAddress(t),
			MaxReceiveMessageSize: 1024,
			MaxSendMessageSize:    1024,
		},
	}
	if err := resourceSlot.Rebuild(context.Background(), cfg); err != nil {
		t.Fatalf("initial grpc build failed, errmsg: %s", err)
	}

	cfg.Grpc.MaxReceiveMessageSize = 2048
	done := make(chan error, 1)
	go func() { done <- resourceSlot.Rebuild(context.Background(), cfg) }()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("grpc parameter rebuild failed, errmsg: %s", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("grpc parameter rebuild did not release the reused listener")
	}
	resourceSlot.Close(context.Background())
}

func TestGRPCSlotReleasesOldAddressAfterSwap(t *testing.T) {
	service := &Service{shutdown: make(chan struct{})}
	service.grpcSvc = NewAdminGrpcService(service)
	resourceSlot := newGRPCSlot(service)
	oldAddress := freeGRPCAddress(t)
	cfg := config.Configuration{Grpc: config.GrpcConfig{ListenAddress: oldAddress}}
	if err := resourceSlot.Rebuild(context.Background(), cfg); err != nil {
		t.Fatalf("initial grpc build failed, errmsg: %s", err)
	}

	cfg.Grpc.ListenAddress = freeGRPCAddress(t)
	if err := resourceSlot.Rebuild(context.Background(), cfg); err != nil {
		t.Fatalf("grpc address rebuild failed, errmsg: %s", err)
	}
	listener, err := net.Listen("tcp", oldAddress)
	if err != nil {
		t.Fatalf("old grpc address was not released, errmsg: %s", err)
	}
	_ = listener.Close()
	resourceSlot.Close(context.Background())
}

func TestGRPCSlotKeepsOldListenerWhenNewAddressFails(t *testing.T) {
	service := &Service{shutdown: make(chan struct{})}
	service.grpcSvc = NewAdminGrpcService(service)
	resourceSlot := newGRPCSlot(service)
	oldAddress := freeGRPCAddress(t)
	cfg := config.Configuration{Grpc: config.GrpcConfig{ListenAddress: oldAddress}}
	if err := resourceSlot.Rebuild(context.Background(), cfg); err != nil {
		t.Fatalf("initial grpc build failed, errmsg: %s", err)
	}

	occupied := occupyAddress(t)
	defer occupied.Close()
	cfg.Grpc.ListenAddress = occupied.Addr().String()
	if err := resourceSlot.Rebuild(context.Background(), cfg); err == nil {
		t.Fatal("rebuild to occupied address should fail")
	}
	if resourceSlot.fp.ListenAddress != oldAddress {
		t.Fatalf("fp listen address: %s, want old address", resourceSlot.fp.ListenAddress)
	}
	assertGRPCAccepts(t, oldAddress)
	resourceSlot.Close(context.Background())
}

func TestGRPCSlotCanceledContextDoesNotSwap(t *testing.T) {
	service := &Service{shutdown: make(chan struct{})}
	service.grpcSvc = NewAdminGrpcService(service)
	resourceSlot := newGRPCSlot(service)
	cfg := config.Configuration{Grpc: config.GrpcConfig{ListenAddress: freeGRPCAddress(t)}}
	if err := resourceSlot.Rebuild(context.Background(), cfg); err != nil {
		t.Fatalf("initial grpc build failed, errmsg: %s", err)
	}
	before := resourceSlot.fp

	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	cfg.Grpc.MaxReceiveMessageSize = 4096
	if err := resourceSlot.Rebuild(ctx, cfg); err == nil {
		t.Fatal("canceled context should fail rebuild")
	}
	if resourceSlot.fp != before {
		t.Fatal("canceled rebuild must not change fingerprint")
	}
	resourceSlot.Close(context.Background())
}

func TestGRPCSlotParameterRebuildRecoversWhenStartFails(t *testing.T) {
	service := &Service{shutdown: make(chan struct{})}
	service.grpcSvc = NewAdminGrpcService(service)
	resourceSlot := newGRPCSlot(service)
	cfg := config.Configuration{
		Grpc: config.GrpcConfig{
			ListenAddress:         freeGRPCAddress(t),
			MaxReceiveMessageSize: 1024,
		},
	}
	if err := resourceSlot.Rebuild(context.Background(), cfg); err != nil {
		t.Fatalf("initial grpc build failed, errmsg: %s", err)
	}

	resourceSlot.startGenerationHook = func(listener net.Listener, hookCfg config.GrpcConfig) (*grpcGeneration, error) {
		if hookCfg.MaxReceiveMessageSize == 2048 {
			return nil, errors.New("start failed")
		}
		return defaultStartGeneration(resourceSlot, listener, hookCfg)
	}
	cfg.Grpc.MaxReceiveMessageSize = 2048
	err := resourceSlot.Rebuild(context.Background(), cfg)
	if err == nil {
		t.Fatal("parameter rebuild should fail when startGeneration fails")
	}
	if resourceSlot.fp.MaxReceiveMessageSize != 1024 {
		t.Fatalf("fp should stay on old parameters, got: %d", resourceSlot.fp.MaxReceiveMessageSize)
	}
	resourceSlot.Close(context.Background())
}

func defaultStartGeneration(
	slot *grpcSlot,
	listener net.Listener,
	cfg config.GrpcConfig,
) (*grpcGeneration, error) {
	slot.startGenerationHook = nil
	return slot.startGeneration(listener, cfg)
}

func occupyAddress(t *testing.T) net.Listener {
	t.Helper()
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("occupy address failed, errmsg: %s", err)
	}
	return listener
}

func assertGRPCAccepts(t *testing.T, address string) {
	t.Helper()
	done := make(chan error, 1)
	go func() {
		conn, err := net.DialTimeout("tcp", address, time.Second)
		if err != nil {
			done <- err
			return
		}
		_ = conn.Close()
		done <- nil
	}()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("old grpc address should still accept, errmsg: %s", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("old grpc address did not accept")
	}
}

func freeGRPCAddress(t *testing.T) string {
	t.Helper()
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("reserve grpc address failed, errmsg: %s", err)
	}
	address := listener.Addr().String()
	if err := listener.Close(); err != nil {
		t.Fatalf("release grpc address failed, errmsg: %s", err)
	}
	return address
}
