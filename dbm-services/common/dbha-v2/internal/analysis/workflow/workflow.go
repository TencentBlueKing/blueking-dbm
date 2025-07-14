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
	"dbm-services/common/dbha-v2/internal/analysis/notifier"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/pkg/logger"
	"time"
)

const (
	scanIntervalLimitMin = 5 * time.Second
)

type Workflow struct {
	cdbStragety  *changeDBStrategy
	dbcache      *dbMetadataCache
	cdb          *changeDB
	db           *storage.Storage
	notifierAsst notifier.Notifier
	cfg          config.WorkflowConfig
	quit         chan struct{}
}

func New(cfg config.WorkflowConfig, db *storage.Storage, asst notifier.Notifier) (*Workflow, error) {
	strategy := &changeDBStrategy{}
	metadataCache := &dbMetadataCache{}

	wflow := &Workflow{
		cdbStragety:  strategy,
		dbcache:      metadataCache,
		notifierAsst: asst,
		db:           db,
		cfg:          cfg,
		quit:         make(chan struct{}, 1),
	}

	return wflow, nil
}

func (w *Workflow) lockBusiness() error {
	return nil
}

func (w *Workflow) unlockBusiness() error {
	return nil
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
		}
	}
}

func (w *Workflow) Close() {
	if w.quit != nil {
		close(w.quit)
	}
	w.quit = nil

}
