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
	"dbm-services/common/dbha-v2/internal/analysis/notifier"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/workflow"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
)

type Service struct {
	db           *storage.Storage
	wflow        *workflow.Workflow
	notifierAsst notifier.Notifier
}

func (s *Service) Run(ctx context.Context) error {
	if len(config.Cfg.Storage) == 0 {
		return gerrors.Newf(gerrors.InvalidConfiguration, "not set any inputter")
	}

	// 1. create storage
	sdb, err := storage.New(config.Cfg.Storage)
	if err != nil {
		logger.Error("create storage failed, errmsg(%v)", err)
		return err
	}
	s.db = sdb
	defer s.db.Close()

	// 2. create notifier
	notifierAsst, err := notifier.New()
	if err != nil {
		logger.Error("create notifier failed, errmsg(%v)", err)
		return err
	}
	s.notifierAsst = notifierAsst
	defer s.notifierAsst.Close()

	// 3. create workflow
	wflow, err := workflow.New(config.Cfg.Workflow, s.db, s.notifierAsst)
	if err != nil {
		logger.Error("create workflow failed, errmsg(%v)", err)
		return err
	}
	s.wflow = wflow
	defer s.wflow.Close()

	// 4. run workflow
	return s.wflow.Run(ctx)
}

func (s *Service) Close() {
	s.wflow.Close()

	if s.notifierAsst != nil {
		s.notifierAsst.Close()
	}
}
