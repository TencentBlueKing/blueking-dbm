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
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
)

const (
	scanIntervalLimitMin = 5 * time.Second
)

type Workflow struct {
	hadata       *DbhaData
	dbmMetadata  *DbmMetadata
	discoveryCli *discovery.Client
	cfg          config.WorkflowConfig
	quit         chan struct{}
	wg           sync.WaitGroup
}

func New(cfg config.WorkflowConfig, cli *discovery.Client, db *hamysql.DB) (*Workflow, error) {
	wflow := &Workflow{
		hadata: &DbhaData{
			db: db,
		},

		dbmMetadata: &DbmMetadata{
			db:           db,
			discoveryCli: cli,
		},

		cfg:          cfg,
		discoveryCli: cli,
		quit:         make(chan struct{}, 1),
	}

	return wflow, nil
}

func (w *Workflow) checkBusiness(ctx context.Context, bizID int) (retErr error) {
	logger.Debug("check the business: %d", bizID)

	//  Acquire the lock to ensuer the only one instance of the AM handles the bizID.
	mu, retErr := w.discoveryCli.CreateMutex(strconv.Itoa(bizID))
	if retErr != nil {
		return retErr
	}
	defer mu.Close()

	if retErr = mu.TryLock(ctx); retErr != nil {
		return retErr
	}

	defer func() {
		if retErr = mu.Unlock(ctx); retErr != nil {
			logger.Error("failed to unlock the biz: %d, errmsg: %v", bizID, retErr)
		}
	}()

	metaData, retErr := w.hadata.readMetadataCacheWithBizID(bizID, 1000)
	if retErr != nil {
		return retErr
	}

	for _, meta := range metaData {
		logger.Debug("check the business: %d, bk cloud id: %d ip: %s port: %d",
			meta.BkBizID, meta.BkCloudID, meta.IP, meta.Port)
	}

	return retErr
}

func (w *Workflow) scanBusinesses(ctx context.Context) {
	bizIDs, err := w.hadata.getBizIDs()
	if err != nil {
		logger.Warn("get business ids failed, %v", err)
		return
	}

	wgBizs := sync.WaitGroup{}
	for _, bizID := range bizIDs {
		wgBizs.Add(1)

		go func(bizID int) {
			defer wgBizs.Done()

			if err := w.checkBusiness(ctx, bizID); err != nil {
				// TODO: notify admin
			}

		}(bizID)
	}

	wgBizs.Wait()
}

func (w *Workflow) Run(ctx context.Context) error {
	if w.cfg.ScanInterval < scanIntervalLimitMin {
		logger.Warn("scan interval(%v) is too small,reset it to the default value(%v)",
			w.cfg.ScanInterval, scanIntervalLimitMin)

		w.cfg.ScanInterval = scanIntervalLimitMin
	}

	if err := w.dbmMetadata.Run(ctx); err != nil {
		logger.Error("failed to run the dbm metadata manager, errmsg: %v", err)
		return err
	}

	w.wg.Add(1)

	go func() {
		defer w.wg.Done()
		timer := time.NewTimer(w.cfg.ScanInterval)
		defer timer.Stop()

		for {
			select {
			case <-w.quit:
				return

			case <-ctx.Done():
				return

			case <-timer.C:
				w.scanBusinesses(ctx)
				timer.Reset(w.cfg.ScanInterval)
			}
		}
	}()

	return nil
}

func (w *Workflow) Close() {
	if w.quit != nil {
		close(w.quit)
	}

	w.wg.Wait()
	w.quit = nil
}
