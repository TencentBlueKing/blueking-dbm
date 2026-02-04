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

package analysis

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/workflow"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/hako/durafmt"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.uber.org/zap"
)

const (
	Name = "analysis"
)

type Service struct {
	quit         chan struct{}
	info         discovery.ServiceInfo
	engine       *gin.Engine
	httpApmSvr   *http.Server
	discoveryCli *discovery.Client
	discovery    *discovery.Discovery
	regCli       *discovery.Registry
	wflow        *workflow.Workflow
	db           *hamysql.GormDB
	wg           sync.WaitGroup
	etcdLogger   *zap.Logger
	gormLogger   logger.Logger
}

func (s *Service) Run(ctx context.Context) error {
	ips, err := machine.GetLocalIPs()
	if err != nil {
		return err
	}

	s.info.Name = Name
	s.info.ID = uuid.New().String()
	s.info.StartTime = time.Now().Local()
	s.info.IPs = ips

	// create discovery client
	if err := s.createDiscovery(); err != nil {
		return err
	}

	// create db storage
	if err := s.createStorage(); err != nil {
		return err
	}

	// create notifier
	if err := s.createNotifier(); err != nil {
		return err
	}

	// create workflow
	if err := s.createWorkflow(ctx); err != nil {
		return err
	}

	// create apm server
	if err := s.createApmServer(); err != nil {
		return err
	}

	if err := haapm.AppStartupMetric.Set(float64(s.info.StartTime.Unix())); err != nil {
		logger.Warn("failed to update the startup time for this process, errmsg: %s", err)
	}

	if s.quit == nil {
		s.quit = make(chan struct{})
	}

	timerTimeout := 3 * time.Second
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
			timer.Reset(timerTimeout)
		}
	}
}

func (s *Service) Close() {
	s.wflow.Close()
	if s.discovery != nil {
		s.discovery.Close()
		s.discovery = nil
	}
	if s.httpApmSvr != nil {
		timeout := max(config.Cfg.Apm.ReadTimeout, config.Cfg.Apm.WriteTimeout)

		ctx, cancel := context.WithTimeout(context.Background(), timeout)
		defer cancel()
		if err := s.httpApmSvr.Shutdown(ctx); err != nil {
			logger.Fatal("failed to shutdown the apm server, errmsg: %s", err)
		}
	}

	s.wg.Wait()
	logger.Info("exited from the analysis service")
}

func (s *Service) createDiscovery() error {
	cli, err := discovery.NewClientWithOptions(
		discovery.OptionEndpoints(strings.Split(config.Cfg.Discovery.Endpoint, constant.Delimiter)),
		discovery.OptionUser(config.Cfg.Discovery.User),
		discovery.OptionPassword(config.Cfg.Discovery.Password),
		discovery.OptionServiceName(s.info.Name),
		discovery.OptionServiceID(s.info.ID),
		discovery.OptionLogger(s.etcdLogger),
	)

	if err != nil {
		return err
	}
	s.discoveryCli = cli

	disc, err := cli.CreateDiscovery()
	if err != nil {
		return err
	}
	s.discovery = disc

	s.regCli = cli.CreateRegistry()
	s.updateInfo()
	return nil
}

func (s *Service) createApmServer() error {
	trace.Setup()

	if s.engine == nil {
		gin.SetMode(gin.ReleaseMode)
		s.engine = gin.Default()
		s.engine.Use(otelgin.Middleware("dbha-v2-analysis"))
	}

	if s.httpApmSvr == nil {
		s.httpApmSvr = &http.Server{
			Handler:      s.engine,
			Addr:         config.Cfg.Apm.ListenAddress,
			ReadTimeout:  config.Cfg.Apm.ReadTimeout,
			WriteTimeout: config.Cfg.Apm.WriteTimeout,
		}
	}

	apm.InitAPM(s.info.ID, s.info.Name)
	metric.NewPrometheus("dbha-v2-analysis", apm.Metrics).Use(s.engine)

	s.wg.Add(1)
	go func() {
		s.wg.Done()
		if err := s.httpApmSvr.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("failed to run apm server, errmsg: %s", err)
		}
		logger.Info("exited from the apm server")
	}()
	return nil
}

func (s *Service) updateInfo() {
	s.info.UpdatedAt = time.Now().Local()
	s.info.Uptime = durafmt.Parse(time.Now().Local().Sub(s.info.StartTime)).String()

	data, err := json.Marshal(s.info)
	if err != nil {
		logger.Warn("failed to marshal service info to json, errmsg: %v", err)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	if err = s.regCli.SetService(ctx, string(data)); err != nil {
		logger.Warn("failed to update the service info in the registry, errmsg: %v", err)
	}
}

func (s *Service) createStorage() error {
	epoint, err := hanet.NewEndpoint(config.Cfg.Storage.Endpoint)
	if err != nil {
		logger.Error("invalid storage configuration, %v", err)
		return gerrors.Newf(gerrors.InvalidConfiguration, "invalid storage configuration, %v", err)
	}

	db, err := hamysql.NewGormDB(
		hamysql.OptionProto(epoint.Proto),
		hamysql.OptionIP(epoint.Host),
		hamysql.OptionPort(epoint.Port),
		hamysql.OptionDBName(hamodel.DatabaseName),
		hamysql.OptionUser(config.Cfg.Storage.User),
		hamysql.OptionPassword(config.Cfg.Storage.Password),
		hamysql.OptionLogger(s.gormLogger),
	)

	if err != nil {
		logger.Warn("create mysql storage failed, %v", err)
		return err
	}

	s.db = db
	return nil
}

func (s *Service) createNotifier() error {
	monitor.SetDataID(config.Cfg.Monitor.DataID)
	monitor.SetEndpoint(config.Cfg.Monitor.BkMonitorEndpoint)
	monitor.SetBkMonitorBeat(config.Cfg.Monitor.BkMonitorBeat)
	monitor.SetAccessToken(config.Cfg.Monitor.AccessToken)
	return nil
}

func (s *Service) createWorkflow(ctx context.Context) error {
	wflow, err := workflow.New(s.discoveryCli, s.db, s.discovery, s.discoveryCli.GetSelfPrefix(), s.info.ID)
	if err != nil {
		return err
	}
	s.wflow = wflow

	return s.wflow.Run(ctx)
}
