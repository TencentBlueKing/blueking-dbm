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

package example

import (
	"context"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/logger"
	"sync"
	"time"
)

type ExampleData struct {
	CPU       float64
	MEM       float64
	ReadQPS   int
	WriteQPS  int
	Timestamp uint64
}

type Example struct {
	// NOTE: Must include UnimplementedMethod
	plugin.UnimplementedMethod
	wg sync.WaitGroup
}

func NewExample(opts ...Option) *Example {
	expOpts := defaultExampleOptions

	for _, opt := range opts {
		opt.apply(&expOpts)
	}

	logger.Info("expOpts:%v", expOpts)

	return &Example{}
}

func (e *Example) Name() (string, error) {
	return "example", nil
}

func (e *Example) Version() (string, error) {
	return "v1.0.0", nil
}

func (e *Example) Harvest(ctx context.Context) (<-chan *plugin.HarvestData, error) {
	// NOTE: Do not block Harvest method.

	dataC := make(chan *plugin.HarvestData, 1024)

	e.wg.Add(1)
	go func(ctx context.Context) {
		defer e.wg.Done()
		defer close(dataC)
		ticker := time.NewTicker(5 * time.Second)

		for {
			select {
			case <-ctx.Done():
				logger.Info("exit example harvest plugin")
				return

			case <-ticker.C:
				// collect data from the target database instance.
				data := &plugin.HarvestData{
					Data: &ExampleData{
						CPU:       10,
						MEM:       11,
						ReadQPS:   100,
						WriteQPS:  200,
						Timestamp: uint64(time.Now().Unix()),
					},
				}

				// report data
				dataC <- data
			}
		}

	}(ctx)

	return dataC, nil
}

func (e *Example) Close() error {
	e.wg.Wait()
	return nil
}
