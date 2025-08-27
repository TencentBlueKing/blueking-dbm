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
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/workflow"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"github.com/google/uuid"
	"github.com/hako/durafmt"
	"go.uber.org/zap"
)

const (
	Name = "analysis"
)

type Service struct {
	quit         chan struct{}
	info         discovery.ServiceInfo
	discoveryCli *discovery.Client
	regCli       *discovery.Registry
	wflow        *workflow.Workflow
	db           *hamysql.DB
	logger       *zap.Logger // only for the gRPC
}

func (s *Service) createDiscovery() error {
	cli, err := discovery.NewClientWithOptions(
		discovery.OptionEndpoints(strings.Split(config.Cfg.Discovery.Endpoint, ";")),
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

	db, err := hamysql.New(
		hamysql.OptionProto(epoint.Proto),
		hamysql.OptionIP(epoint.Host),
		hamysql.OptionPort(epoint.Port),
		hamysql.OptionDBName(hamodel.DatabaseName),
		hamysql.OptionUser(config.Cfg.Storage.User),
		hamysql.OptionPassword(config.Cfg.Storage.Password),
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
	wflow, err := workflow.New(config.Cfg.Workflow, s.discoveryCli, s.db)
	if err != nil {
		return err
	}
	s.wflow = wflow

	return s.wflow.Run(ctx)
}

func (s *Service) Run(ctx context.Context) error {
	s.info.Name = Name
	s.info.ID = uuid.New().String()
	s.info.StartTime = time.Now().Local()

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
}
