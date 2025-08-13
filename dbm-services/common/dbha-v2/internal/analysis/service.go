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
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/workflow"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"encoding/json"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/hako/durafmt"
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
	dbs          []*hamysql.DB
}

func (s *Service) createDiscovery() error {
	cli, err := discovery.NewClientWithOptions(
		discovery.OptionEndpoints(strings.Split(config.Cfg.Discovery.Endpoint, ";")),
		discovery.OptionUser(config.Cfg.Discovery.User),
		discovery.OptionPassword(config.Cfg.Discovery.Password),
		discovery.OptionServiceName(s.info.Name),
		discovery.OptionServiceID(s.info.ID),
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
		logger.Warn("failed to update the service info in the registry, errmsg: %v", err)
	}
}

func (s *Service) createStorage() error {
	epoints, err := hanet.NewEndpoints(config.Cfg.Storage.Endpoint)
	if err != nil {
		logger.Error("invalid storage configuration, %v", err)
		return gerrors.Newf(gerrors.InvalidConfiguration, "invalid storage configuration, %v", err)
	}

	for _, epoint := range epoints {
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
			continue
		}

		s.dbs = append(s.dbs, db)
	}

	if len(s.dbs) == 0 {
		logger.Error("not any usable db, endpoints(%s)", config.Cfg.Storage.Endpoint)
		return gerrors.Newf(gerrors.ComponentFailure, "not any usable db, endpoints(%s)", config.Cfg.Storage.Endpoint)
	}

	return nil
}

func (s *Service) createNotifier() error {
	return nil
}

func (s *Service) createWorkflow() error {
	wflow, err := workflow.New(config.Cfg.Workflow, s.dbs)
	if err != nil {
		return err
	}
	s.wflow = wflow
	return nil
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
	if err := s.createWorkflow(); err != nil {
		return err
	}

	// run workflow
	if err := s.wflow.Run(ctx); err != nil {
		return err
	}

	ticker := time.NewTicker(3 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-s.quit:
			return nil

		case <-ctx.Done():
			return nil

		case <-ticker.C:
			s.updateInfo()
		}
	}
}

func (s *Service) Close() {
	s.wflow.Close()
}
