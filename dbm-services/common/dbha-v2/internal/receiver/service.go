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
	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/internal/receiver/input"
	"dbm-services/common/dbha-v2/internal/receiver/output"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"sync"
)

type Service struct {
	inputers  []input.Inputer
	outputers []output.Outputer
}

func (s *Service) Run(ctx context.Context) error {
	if len(config.Cfg.Inputers) == 0 {
		return gerrors.New(gerrors.InvalidConfiguration, "not set any inputer")
	}

	if len(config.Cfg.Outputers) == 0 {
		return gerrors.New(gerrors.InvalidConfiguration, "not set any outputer")
	}

	for _, outputerCfg := range config.Cfg.Outputers {
		if !outputerCfg.Enable {
			logger.Info("the outputer(%s) is disabled", outputerCfg.Name)
			continue
		}

		outputer, err := output.NewOutputer(outputerCfg)
		if err != nil {
			logger.Warn("create new outputer(%s) failed, errmsg(%v)", outputerCfg.Name, err)
			continue
		}

		s.outputers = append(s.outputers, outputer)
	}

	for _, inputerCfg := range config.Cfg.Inputers {
		if !inputerCfg.Enable {
			logger.Info("the inputer(%s) is disabled", inputerCfg.Name)
			continue
		}

		inputer, err := input.NewInputer(inputerCfg)
		if err != nil {
			logger.Warn("create new inputer(%s) failed, errmsg(%v)", inputerCfg.Name, err)
			continue
		}

		err = inputer.Harvest(s.outputers)
		if err != nil {
			logger.Warn("do not start harvest for inputer(%s), errmsg(%v)", inputerCfg.Name, err)
			continue
		}

		s.inputers = append(s.inputers, inputer)
	}

	return nil
}

func (s *Service) Close() {
	wg := sync.WaitGroup{}

	for _, inputer := range s.inputers {
		wg.Add(1)
		go func(in input.Inputer) {
			defer wg.Done()
			in.Close()
		}(inputer)
	}

	for _, outputer := range s.outputers {
		wg.Add(1)
		go func(out output.Outputer) {
			wg.Done()
			out.Close()
		}(outputer)
	}

	wg.Wait()
}
