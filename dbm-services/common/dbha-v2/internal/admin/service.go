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
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/apm"
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/slot"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/go-pubpkg/apm/trace"

	"github.com/google/uuid"
	"go.uber.org/zap"
)

var processAPMInit sync.Once

// Name returns the process name from the current executable (same as Makefile binary name).
func Name() string {
	return "admin"
}

// Service is the admin service. It references AdminGrpcService and manages its lifecycle;
// gRPC API is served by AdminGrpcService.
type Service struct {
	quit             chan struct{}
	info             discovery.ServiceInfo
	grpcSvc          *AdminGrpcService // gRPC API implementation, created and owned by Service
	logger           *zap.Logger
	gormLogger       logger.Logger
	runtimeLogger    *logger.DbmLogger
	configPath       string
	pidFile          string
	reloadC          chan struct{}
	reloadWorkerDone chan struct{}
	shutdown         chan struct{}
	infoMu           sync.Mutex
	closeOnce        sync.Once
	apmSlot          *slot.Slot[haapm.Server]
	discoverySlot    *slot.Slot[discoveryResource]
	storageSlot      *slot.Slot[storageResource]
	webSlot          *slot.Slot[hanet.GinHTTPServer]
	grpcSlot         *grpcSlot
	slots            []slot.Ops
}

// Run run admin service
func (s *Service) Run(ctx context.Context) error {
	ips, err := machine.GetLocalIPs()
	if err != nil {
		return err
	}

	s.info.Name = Name()
	s.info.ID = uuid.New().String()
	s.info.StartTime = time.Now().Local()
	s.info.IPs = ips

	processAPMInit.Do(func() {
		trace.Setup()
		apm.InitAPM(s.info.ID, s.info.Name)
	})
	s.grpcSvc = NewAdminGrpcService(s)
	s.initSlots()
	if err := s.startSlots(ctx, config.Snapshot()); err != nil {
		return err
	}

	if err := haapm.AppStartupMetric.Set(float64(s.info.StartTime.Unix())); err != nil {
		logger.Warn("failed to update the startup time for this process, errmsg: %s", err)
	}

	if s.quit == nil {
		s.quit = make(chan struct{})
	}

	timerTimeout := config.Snapshot().Discovery.ServiceTimerInterval
	if timerTimeout == 0 {
		timerTimeout = constant.DefaultServiceTimerInterval
	}
	timer := time.NewTimer(timerTimeout)
	defer timer.Stop()

	for {
		select {
		case <-s.quit:
			return nil

		case <-ctx.Done():
			return nil

		case <-timer.C:
			s.updateInfo()
			timerTimeout = config.Snapshot().Discovery.ServiceTimerInterval
			if timerTimeout == 0 {
				timerTimeout = constant.DefaultServiceTimerInterval
			}
			timer.Reset(timerTimeout)
		}
	}
}

// Close close admin service
func (s *Service) Close() {
	s.closeOnce.Do(func() {
		closeSignal(s.shutdown)
		closeSignal(s.quit)
		if s.reloadWorkerDone != nil {
			<-s.reloadWorkerDone
		}
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		s.closeSlots(ctx, len(s.slots))
		s.grpcSvc = nil
	})
}

func (s *Service) startSlots(ctx context.Context, cfg config.Configuration) error {
	for index, resourceSlot := range s.slots {
		if s.isShuttingDown() {
			s.closeSlots(ctx, index)
			return context.Canceled
		}
		if err := resourceSlot.Rebuild(ctx, cfg); err != nil {
			s.closeSlots(ctx, index)
			return err
		}
	}
	return nil
}

func (s *Service) closeSlots(ctx context.Context, count int) {
	for index := count - 1; index >= 0; index-- {
		s.slots[index].Close(ctx)
	}
}

func (s *Service) updateInfo() {
	resource := s.discoverySlot.Get()
	if resource == nil || resource.registry == nil {
		return
	}
	updateTimeout := config.Snapshot().Discovery.ServiceUpdateTimeout
	if updateTimeout == 0 {
		updateTimeout = constant.DefaultServiceUpdateTimeout
	}
	ctx, cancel := context.WithTimeout(context.Background(), updateTimeout)
	defer cancel()
	if err := s.setServiceInfo(ctx, resource.registry); err != nil {
		logger.Warn("failed to update the service info in the registry, errmsg: %s", err)
	}
}

func (s *Service) isShuttingDown() bool {
	if s.shutdown == nil {
		return false
	}
	select {
	case <-s.shutdown:
		return true
	default:
		return false
	}
}

func closeSignal(signal chan struct{}) {
	if signal == nil {
		return
	}
	select {
	case <-signal:
	default:
		close(signal)
	}
}
