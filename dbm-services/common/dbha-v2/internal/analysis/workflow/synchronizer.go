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

package workflow

import (
	"context"
	"encoding/json"
	"errors"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const (
	maxCountPerPage = 200
	electionName    = "sync-dbm-metadata"
)

type Synchronizer struct {
	db           *hamysql.GormDB
	cli          *dbm.Client
	wg           sync.WaitGroup
	discoveryCli *discovery.Client
}

func (s *Synchronizer) Run(ctx context.Context) error {
	if s.cli == nil {
		s.cli = &dbm.Client{}
	}

	if err := s.updateCache(ctx); err != nil {
		return err
	}

	return nil
}

func (s *Synchronizer) Close() {
	s.wg.Wait()
}

// QueryMetadataFromDbm queries metadata from DBM for the given cloud and IPs.
func (s *Synchronizer) QueryMetadataFromDbm(ctx context.Context, bkCloudID int, ips []string) ([]*dbm.DbInstMetadata, error) {
	if s.cli == nil {
		return nil, errors.New("dbm client not initialized")
	}
	return s.cli.QueryMetadataFromDbm(ctx, bkCloudID, ips)
}

func (s *Synchronizer) saveRespond(resp *dbm.Response) error {
	datas := []*hamodel.DbmMetadata{}
	for _, rsp := range resp.Data {
		meta := &hamodel.DbmMetadata{
			BkIdcCityID:     rsp.BkIdcCityID,
			BkBizID:         rsp.BkBizID,
			BkCloudID:       rsp.BkCloudID,
			LogicalCityID:   rsp.LogicalCityID,
			LogicalCityName: rsp.LogicalCityName,
			Port:            rsp.Port,
			AdminPort:       rsp.AdminPort,
			IP:              rsp.IP,
			Cluster:         rsp.Cluster,
			ClusterID:       rsp.ClusterID,
			ClusterType:     rsp.ClusterType,
			MachineType:     rsp.MachineType,
			Status:          string(rsp.Status),
			InstanceRole:    string(rsp.InstanceRole),
		}

		if rsp.Receiver != nil {
			if data, err := json.Marshal(rsp.Receiver); err != nil {
				logger.Warn("failed to marshal the receiver, errmsg: %s", err)
			} else {
				meta.Receiver = string(data)
			}
		}

		if data, err := json.Marshal(rsp.BindEntry); err != nil {
			logger.Warn("failed to marshal the bind entry, errmsg: %s", err)
		} else {
			meta.BindEntry = string(data)
		}

		if rsp.ProxyInstanceSet != nil {
			if data, err := json.Marshal(rsp.ProxyInstanceSet); err != nil {
				logger.Warn("failed to marshal the proxy insts, errmsg: %s", err)
			} else {
				meta.ProxyInstanceSet = string(data)
			}
		}

		if rsp.BinlogDumpers != nil {
			if data, err := json.Marshal(rsp.BinlogDumpers); err != nil {
				logger.Warn("failed to marshal the binlog dumpers, errmsg: %s", err)
			} else {
				meta.BinlogDumperSet = string(data)
			}
		}

		datas = append(datas, meta)
	}

	err := s.db.DB().Session(&gorm.Session{FullSaveAssociations: true}).
		Clauses(clause.OnConflict{UpdateAll: true}).
		Create(datas).Error

	return err
}

func (s *Synchronizer) syncMetadataFromDbm(ctx context.Context) error {
	req := dbm.DefaultRequest
	req.HashCnt = maxCountPerPage
	req.DbCloudToken = config.Cfg.Workflow.DbmApiMetadata.Token
	req.Statuses = []string{string(dbm.Running), string(dbm.Available)}

	for idx := range maxCountPerPage {
		req.HashValue = idx

		metaRsp, err := s.cli.RequestMetadata(ctx, &req)
		if err != nil {
			if errors.Is(err, dbm.ErrNoResponse) {
				continue
			}

			logger.Warn("failed to request the metadata from DBM, API: %s, req: %v, errmsg: %s",
				config.Cfg.Workflow.DbmApiMetadata.Api, req, err)

			continue
		}

		if err := s.saveRespond(metaRsp); err != nil {
			logger.Warn("failed to save the metadata: %v, errmsg: %v", metaRsp, err)
		}
	}

	return nil
}

func (s *Synchronizer) updateCache(ctx context.Context) error {
	if err := s.syncMetadataFromDbm(ctx); err != nil {
		logger.Warn("faled to sync metadata from dbm, errmsg: %v", err)
	}

	election, err := s.discoveryCli.CreateElection(electionName)
	if err != nil {
		return err
	}

	s.wg.Add(1)
	go func() {
		defer s.wg.Done()

		if err := election.Campaign(ctx); err != nil {
			election.Close()
			logger.Warn("election failure, errmsg: %v", err)
			election = nil
		}

		timer := time.NewTimer(config.Cfg.Workflow.UpdateDbmCacheInterval)

		for {
			if election == nil {
				election, err = s.discoveryCli.CreateElection(electionName)
				if err != nil {
					logger.Warn("election failure, errmsg: %v", err)
					time.Sleep(100 * time.Millisecond)
					continue
				}

				if err := election.Campaign(ctx); err != nil {
					election.Close()
					logger.Warn("election failure, errmsg: %v", err)
					election = nil
					time.Sleep(100 * time.Millisecond)
					continue
				}
			}

			select {
			case <-election.Done():
				election.Close()
				logger.Warn("network anomaly requires a re-election")
				election = nil

			case <-ctx.Done():
				election.Close()
				logger.Info("exit dbm metadata manager")
				return

			case <-timer.C:
				if err := s.syncMetadataFromDbm(ctx); err != nil {
					logger.Warn("faled to query metadata from dbm, errmsg: %v", err)
				}

				timer.Reset(config.Cfg.Workflow.UpdateDbmCacheInterval)
			}
		}
	}()

	return nil
}
