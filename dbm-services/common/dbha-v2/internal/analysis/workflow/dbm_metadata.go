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
	"net/http"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const (
	minUpdateDbmCacheInterval = 5 * time.Second
	maxCountPerPage           = 200
	electionName              = "sync-dbm-metadata"
)

type DbmMetadata struct {
	db           *hamysql.DB
	httpCli      *hanet.HttpClient
	wg           sync.WaitGroup
	discoveryCli *discovery.Client
}

func (dbm *DbmMetadata) saveRespond(resp *dbmRespond) error {
	datas := []*hamodel.DbmMetadata{}
	for _, rsp := range resp.Data {
		meta := &hamodel.DbmMetadata{
			BkIdcCityID:     rsp.BkIdcCityID,
			BkBizID:         rsp.BkBizID,
			BkCloudID:       rsp.BkCloudID,
			LogicalCityID:   rsp.LogicalCityID,
			LogicalCityName: rsp.LogicalCityName,
			Port:            rsp.Port,
			IP:              rsp.IP,
			Cluster:         rsp.Cluster,
			ClusterID:       rsp.ClusterID,
			ClusterType:     rsp.ClusterType,
			MachineType:     rsp.MachineType,
			Status:          rsp.Status,
			BindEntry:       hamodel.BindEntryType{},
		}

		for key, vals := range rsp.BindEntry {
			for _, val := range vals {
				meta.BindEntry[key] = append(meta.BindEntry[key], hamodel.BindEntry{
					BindPort:       val.BindPort,
					BindIps:        val.BindIps,
					Domain:         val.Domain,
					EntryRole:      val.EntryRole,
					ForwardEntryId: val.ForwardEntryId,
					ClbIP:          val.ClbIP,
					ClbID:          val.ClbID,
					ClbListenerID:  val.ClbListenerID,
					ClbRegion:      val.ClbRegion,
				})
			}
		}

		datas = append(datas, meta)
	}

	err := dbm.db.DB().Session(&gorm.Session{FullSaveAssociations: true}).
		Clauses(clause.OnConflict{UpdateAll: true}).
		Create(datas).Error

	return err
}

func (dbm *DbmMetadata) syncMetadataFromDBM(ctx context.Context) error {
	req := defaultDbmRequst
	req.HashCnt = maxCountPerPage
	req.DbCloudToken = config.Cfg.Workflow.DbmApiMetadata.Token

	for idx := range maxCountPerPage {
		req.HashValue = idx

		data, err := json.Marshal(&req)
		if err != nil {
			logger.Warn("failed to marsha the dbm request metadata, errmsg: %v", err)
			continue
		}

		code, resp, err := dbm.httpCli.Post(ctx, config.Cfg.Workflow.DbmApiMetadata.Api, data)
		if err != nil {
			logger.Warn("failed to send http post request, errmsg: %v", err)
			continue
		}

		if http.StatusOK != code {
			logger.Warn("http post request return the bad status, status code: %d, errmsg: %v", code, err)
			continue
		}

		if len(resp) == 0 {
			logger.Warn("response nothing, api: %v", config.Cfg.Workflow.DbmApiMetadata.Api)
			continue
		}

		metaRsp := &dbmRespond{}
		if err := json.Unmarshal(resp, metaRsp); err != nil {
			logger.Warn("failed to unmarshal metadata respond, api: %s, code: %d resp: %s errmsg: %v",
				config.Cfg.Workflow.DbmApiMetadata.Api, code, string(resp), err)
			continue
		}

		if len(metaRsp.Data) == 0 {
			continue
		}

		if err := dbm.saveRespond(metaRsp); err != nil {
			logger.Warn("failed to save the metadata: %v, errmsg: %v", metaRsp, err)
		}
	}

	return nil
}

func (dbm *DbmMetadata) updateCache(ctx context.Context) error {
	if err := dbm.syncMetadataFromDBM(ctx); err != nil {
		logger.Warn("faled to sync metadata from dbm, errmsg: %v", err)
	}

	election, err := dbm.discoveryCli.CreateElection(electionName)
	if err != nil {
		return err
	}

	dbm.wg.Add(1)
	go func() {
		defer dbm.wg.Done()

		if err := election.Campaign(ctx); err != nil {
			election.Close()
			logger.Warn("election failure, errmsg: %v", err)
			election = nil
		}

		timer := time.NewTimer(config.Cfg.Workflow.UpdateDbmCacheInterval)

		for {

			if election == nil {
				election, err = dbm.discoveryCli.CreateElection(electionName)
				if err != nil {
					election.Close()
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
				if err := dbm.syncMetadataFromDBM(ctx); err != nil {
					logger.Warn("faled to query metadata from dbm, errmsg: %v", err)
				}

				timer.Reset(config.Cfg.Workflow.UpdateDbmCacheInterval)
			}
		}
	}()

	return nil
}

func (dbm *DbmMetadata) Run(ctx context.Context) error {
	if dbm.httpCli == nil {
		dbm.httpCli = hanet.NewHttpClientWithHeaders(map[string]string{
			"Content-Type": "application/json",
		})
	}

	if err := dbm.updateCache(ctx); err != nil {
		return err
	}

	return nil
}

func (dbm *DbmMetadata) Close() {
	dbm.wg.Wait()
}
