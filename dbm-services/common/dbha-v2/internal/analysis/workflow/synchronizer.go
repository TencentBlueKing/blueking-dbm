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
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const electionName = "sync-dbm-metadata"

// Synchronizer periodically syncs DBM metadata into the local database cache.
type Synchronizer struct {
	db           *hamysql.GormDB
	cli          *dbm.Client
	wg           sync.WaitGroup
	discoveryCli *discovery.Client
	myServiceID  string
}

// Run starts the metadata synchronization loop.
func (s *Synchronizer) Run(ctx context.Context) error {
	if s.cli == nil {
		s.cli = &dbm.Client{}
	}

	if err := s.updateCache(ctx); err != nil {
		return err
	}

	return nil
}

// Close waits for all background goroutines to finish.
func (s *Synchronizer) Close() {
	s.wg.Wait()
}

// QueryMetadataFromDbm queries metadata from DBM for the given cloud and IPs.
func (s *Synchronizer) QueryMetadataFromDbm(ctx context.Context, bkCloudID int, ips []string) ([]*dbm.DbInstMetadata, error) {
	if s.cli == nil {
		return nil, errors.New("dbm client not initialized")
	}

	// Report DBM API query metadata ip count
	if err := apm.DbmApiQueryMetadataIpCount.SetWithLabels(map[string]string{
		apm.MetricLabelApiName:       apm.MetricApiNameQueryMetadata,
		haapm.MetricLabelServiceID:   s.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(len(ips))); err != nil {
		logger.Warn("failed to report dbm api query metadata ip count metric, errmsg: %s", err)
	}

	start := time.Now()
	code, metadatas, err := s.cli.QueryMetadataFromDbm(ctx, bkCloudID, ips)
	if err != nil {
		var gerr *gerrors.Error
		if errors.As(err, &gerr) {
			code = gerr.Code()
		}

		// Report DBM API query metadata request error
		if reportErr := apm.DbmApiQueryMetadataErrorTotal.IncWithLabels(map[string]string{
			apm.MetricLabelApiName:       apm.MetricApiNameQueryMetadata,
			haapm.MetricLabelServiceID:   s.myServiceID,
			haapm.MetricLabelServiceName: apm.MetricServerName,
			apm.MetricLabelStatusCode:    strconv.Itoa(code),
		}); reportErr != nil {
			logger.Warn("failed to report dbm api request error metric, errmsg: %s", reportErr)
		}
	}
	// Report DBM API query metadata request duration
	if reportErr := apm.DbmApiQueryMetadataTimeConsumingMs.ObserveWithLabels(map[string]string{
		apm.MetricLabelApiName:       apm.MetricApiNameQueryMetadata,
		haapm.MetricLabelServiceID:   s.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
		apm.MetricLabelStatusCode:    strconv.Itoa(code),
	}, float64(time.Since(start).Milliseconds())); reportErr != nil {
		logger.Warn("failed to report dbm api request time consuming metric, errmsg: %s", reportErr)
	}
	return metadatas, err
}

func (s *Synchronizer) saveRespond(resp *dbm.Response) error {
	start := time.Now()
	defer func() {
		// Report DBM metadata updated time consuming
		if reportErr := apm.DbmMetadataSaveTimeConsumingMs.ObserveWithLabels(map[string]string{
			haapm.MetricLabelServiceID:   s.myServiceID,
			haapm.MetricLabelServiceName: apm.MetricServerName,
		}, float64(time.Since(start).Milliseconds())); reportErr != nil {
			logger.Warn("failed to report dbm metadata save time consuming metric, errmsg: %s", reportErr)
		}
	}()

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
			AccessLayer:     rsp.AccessLayer,
			Status:          string(rsp.Status),
			InstanceRole:    rsp.InstanceRole,
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
	start := time.Now()
	hashCnt := config.Cfg.Workflow.DbmApiMetadataHashCnt
	req := dbm.DefaultRequest
	req.HashCnt = hashCnt
	req.DbCloudToken = config.Cfg.Workflow.DbmApiMetadata.Token
	req.Statuses = []string{string(dbm.Running), string(dbm.Available)}

	var hasError bool
	for idx := range hashCnt {
		req.HashValue = idx

		_, metaRsp, err := s.cli.RequestMetadata(ctx, &req)
		if err != nil {
			if errors.Is(err, dbm.ErrNoResponse) {
				continue
			}

			logger.Warn(
				"failed to request metadata from dbm, api: %s, hash_value: %d, errmsg: %s",
				config.Cfg.Workflow.DbmApiMetadata.Api,
				req.HashValue,
				err,
			)

			hasError = true
			continue
		}

		if err := s.saveRespond(metaRsp); err != nil {
			logger.Warn("failed to save metadata, rows: %d, errmsg: %s", len(metaRsp.Data), err)
		}
	}

	s.reportSyncedMetadata(start, hasError)

	return nil
}

func (s *Synchronizer) updateCache(ctx context.Context) error {
	election, err := s.discoveryCli.CreateElection(electionName)
	if err != nil {
		return err
	}

	s.wg.Add(1)
	go func() {
		defer s.wg.Done()

		if err := election.Campaign(ctx); err != nil {
			election.Close()
			logger.Warn("election failure, errmsg: %s", err)
			election = nil
		}

		timer := time.NewTimer(config.Cfg.Workflow.UpdateDbmCacheInterval)

		for {
			if election == nil {
				election, err = s.discoveryCli.CreateElection(electionName)
				if err != nil {
					logger.Warn("election failure, errmsg: %s", err)
					time.Sleep(100 * time.Millisecond)
					continue
				}

				if err := election.Campaign(ctx); err != nil {
					election.Close()
					logger.Warn("election failure, errmsg: %s", err)
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
					logger.Warn("failed to query metadata from dbm, errmsg: %s", err)
				}

				timer.Reset(config.Cfg.Workflow.UpdateDbmCacheInterval)
			}
		}
	}()

	return nil
}

func (s *Synchronizer) reportSyncedMetadata(start time.Time, hasError bool) {
	// Report DBM API sync metadata total
	if reportErr := apm.DbmApiSyncMetadataTotal.IncWithLabels(map[string]string{
		apm.MetricLabelApiName:       apm.MetricApiNameSyncMetadata,
		haapm.MetricLabelServiceID:   s.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}); reportErr != nil {
		logger.Warn("failed to report dbm api sync metadata total metric, errmsg: %s", reportErr)
	}

	// Report DBM API sync metadata request duration
	if reportErr := apm.DbmApiSyncMetadataTimeConsumingMs.ObserveWithLabels(map[string]string{
		apm.MetricLabelApiName:       apm.MetricApiNameSyncMetadata,
		haapm.MetricLabelServiceID:   s.myServiceID,
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(time.Since(start).Milliseconds())); reportErr != nil {
		logger.Warn("failed to report dbm api request time consuming metric, errmsg: %s", reportErr)
	}

	// Report DBM API request error if any error occurred
	if hasError {
		if reportErr := apm.DbmApiSyncMetadataErrorTotal.IncWithLabels(map[string]string{
			apm.MetricLabelApiName:       apm.MetricApiNameSyncMetadata,
			haapm.MetricLabelServiceID:   s.myServiceID,
			haapm.MetricLabelServiceName: apm.MetricServerName,
		}); reportErr != nil {
			logger.Warn("failed to report dbm api request error metric, errmsg: %s", reportErr)
		}
	}
}
