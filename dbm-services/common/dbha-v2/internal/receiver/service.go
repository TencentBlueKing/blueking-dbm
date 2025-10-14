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

package receiver

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/internal/receiver/sink"
	"dbm-services/common/dbha-v2/internal/receiver/source"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/hako/durafmt"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.uber.org/zap"
)

const (
	Name = "receiver"
)

type Service struct {
	quit         chan struct{}
	info         discovery.ServiceInfo
	engine       *gin.Engine
	httpApmSvr   *http.Server
	discoveryCli *discovery.Client
	regCli       *discovery.Registry
	sources      []source.Inputter
	sinks        []sink.Outputter
	wg           sync.WaitGroup
	logger       *zap.Logger // only for the gRPC
}

func (s *Service) Run(ctx context.Context) error {
	s.info.Name = Name
	s.info.ID = uuid.New().String()
	s.info.StartTime = time.Now().Local()

	// create discovery client
	if err := s.createDiscovery(); err != nil {
		return err
	}

	// create sinks
	if err := s.createSinks(); err != nil {
		return err
	}

	// create sources
	if err := s.createSource(ctx); err != nil {
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
	wg := sync.WaitGroup{}

	for _, inputter := range s.sources {
		wg.Add(1)
		go func(in source.Inputter) {
			defer wg.Done()
			in.Close()
		}(inputter)
	}

	for _, outputer := range s.sinks {
		wg.Add(1)
		go func(out sink.Outputter) {
			wg.Done()
			out.Close()
		}(outputer)
	}

	wg.Wait()
	close(s.quit)
	s.quit = nil
}

func (s *Service) createDiscovery() error {
	cli, err := discovery.NewClientWithOptions(
		discovery.OptionEndpoints(strings.Split(config.Cfg.Discovery.Endpoint, constant.Delimiter)),
		discovery.OptionUser(config.Cfg.Discovery.User),
		discovery.OptionPassword(config.Cfg.Discovery.Password),
		discovery.OptionServiceName(s.info.Name),
		discovery.OptionServiceID(s.info.ID),
		discovery.OptionLogger(s.logger),
	)

	if err != nil {
		return err
	}
	s.discoveryCli = cli

	regCli, err := cli.CreateRegistry()
	if err != nil {
		return err
	}
	s.regCli = regCli

	s.updateInfo()
	return nil
}

func (s *Service) updateInfo() {
	if s.info.UpdatedAt.IsZero() {
		s.info.UpdatedAt = time.Now().Local()
	}

	s.info.Uptime = durafmt.Parse(time.Now().Local().Sub(s.info.StartTime)).String()

	data, err := json.Marshal(s.info)
	if err != nil {
		logger.Warn("failed to marshal service info to json, errmsg: %v", err)
		return
	}

	if err = s.regCli.SetService(context.Background(), string(data)); err != nil {
		logger.Warn("failed to udpate the service info in the registry, errmsg: %v", err)
	}
}

func (s *Service) createSource(ctx context.Context) error {
	if len(config.Cfg.Service.Sources) == 0 {
		return gerrors.New(gerrors.InvalidConfiguration, "not set any source")
	}

	for _, sourceCfg := range config.Cfg.Service.Sources {
		if !sourceCfg.Enable {
			logger.Info("the inputer(%s) is disabled", sourceCfg.Name)
			continue
		}

		inputter, err := source.NewInputter(sourceCfg)
		if err != nil {
			logger.Warn("create new inputer(%s) failed, errmsg(%v)", sourceCfg.Name, err)
			continue
		}

		err = inputter.Harvest(ctx, s.sinks)
		if err != nil {
			logger.Warn("do not start harvest for inputer(%s), errmsg(%v)", sourceCfg.Name, err)
			continue
		}

		s.sources = append(s.sources, inputter)
	}

	return nil
}

func (s *Service) createSinks() error {
	if len(config.Cfg.Service.Sinks) == 0 {
		return gerrors.New(gerrors.InvalidConfiguration, "not set any sink")
	}

	for _, sinkCfg := range config.Cfg.Service.Sinks {
		if !sinkCfg.Enable {
			logger.Info("the outputer(%s) is disabled", sinkCfg.Name)
			continue
		}

		outputter, err := sink.NewOutputter(sinkCfg)
		if err != nil {
			logger.Warn("create new outputer(%s) failed, errmsg(%v)", sinkCfg.Name, err)
			continue
		}

		s.sinks = append(s.sinks, outputter)
	}

	return nil
}

func (s *Service) createApmServer() error {
	trace.Setup()

	if s.engine == nil {
		gin.SetMode(gin.ReleaseMode)
		s.engine = gin.Default()
		s.engine.Use(otelgin.Middleware("dbha-v2-receiver"))
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
	metric.NewPrometheus("dbha-v2-receiver", apm.Metrics).Use(s.engine)

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
