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
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/logger"
	"sync"
	"time"
)

const (
	scanIntervalLimitMin = 5 * time.Second
)

type Workflow struct {
	cfg  config.WorkflowConfig
	quit chan struct{}
	wg   sync.WaitGroup
}

func New(cfg config.WorkflowConfig, db *storage.Storage) (*Workflow, error) {

	wflow := &Workflow{
		cfg:  cfg,
		quit: make(chan struct{}, 1),
	}

	return wflow, nil
}

func (w *Workflow) lockBusiness(ctx context.Context, bizID int, timeout time.Duration) error {
	// TODO:
	_ = ctx
	_ = bizID
	_ = timeout

	return nil
}

func (w *Workflow) unlockBusiness(ctx context.Context, bizID int) error {
	// TODO:
	_ = ctx
	_ = bizID

	return nil
}

func (w *Workflow) checkBusiness(ctx context.Context, bizID int) error {
	if err := w.lockBusiness(ctx, bizID, w.cfg.LockBusinessWaitTimeout); err != nil {
	}

	if err := w.unlockBusiness(ctx, bizID); err != nil {
	}

	return nil
}

func (w *Workflow) scanBusinesses(ctx context.Context) {

	bizIDs := []int{}

	for _, bizID := range bizIDs {
		w.wg.Add(1)

		go func(bizID int) {
			defer w.wg.Done()

			if err := w.checkBusiness(ctx, bizID); err != nil {
				// TODO: notify admin
			}

		}(bizID)
	}
}

func (w *Workflow) Run(ctx context.Context) error {
	if w.cfg.ScanInterval < scanIntervalLimitMin {
		logger.Warn("scan interval(%v) is too small,reset it to the default value(%v)",
			w.cfg.ScanInterval, scanIntervalLimitMin)

		w.cfg.ScanInterval = scanIntervalLimitMin
	}

	for {
		select {
		case <-w.quit:
			return nil

		case <-ctx.Done():
			return nil

		case <-time.After(w.cfg.ScanInterval):
			w.scanBusinesses(ctx)
		}
	}
}

func (w *Workflow) Close() {
	if w.quit != nil {
		close(w.quit)
	}

	w.wg.Wait()
	w.quit = nil
}
