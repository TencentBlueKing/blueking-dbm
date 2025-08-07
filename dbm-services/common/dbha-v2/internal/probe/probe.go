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

package probe

import (
	"context"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/internal/probe/reporter"
	"dbm-services/common/dbha-v2/pkg/logger"
	"encoding/json"
	"sync"
	"time"
)

// Probe probe main framework
type Probe struct {
	clientID  string
	machineID string
	serviceID string
	reporters []reporter.Reporter
	plugins   []plugin.Plugin
	quit      chan struct{}
	wg        sync.WaitGroup
}

func (p *Probe) runPlugin(ctx context.Context, plug plugin.Plugin) {
	name, _ := plug.Name()

	defer func() {
		if err := plug.Close(); err != nil {
			logger.Error("exit harvester plugin(%s) failed, %v", name, err)
		}
	}()

	eventC, err := plug.Harvest(ctx, p.machineID, p.serviceID)
	if err != nil {
		logger.Warn("start harvester plugin(%s) failed, %v", name, err)
		return
	}

	for {
		select {
		case <-p.quit:
			return

		case <-ctx.Done():
			return

		case data := <-eventC:
			dataEncoded, err := json.Marshal(data.Value)
			if err != nil {
				logger.Warn("encode data to json failed, plugin(%s), data(%v), %v", name, data.Value, err)
				continue
			}

			for _, r := range p.reporters {
				err := r.Post(ctx, dataEncoded)
				if err == nil {
					// NOTE: Just one reporter sending the data is sufficient.
					break
				}

				logger.Warn("post data to receiver failed, plugin(%s), reporter(%s), %v", name, r.Name(), err)
			}
		}
	}
}

func (p *Probe) loadPlugins(ctx context.Context) error {
	if p.plugins == nil {
		p.plugins = make([]plugin.Plugin, 20)
	}

	for _, cfg := range config.Cfg.Harvesters {
		plug, err := harvester.NewPlugin(cfg)
		if err != nil {
			logger.Warn("create a new harvester plugin(%s) failed, %v", cfg.Name, err)
			continue
		}

		p.wg.Add(1)

		go func() {
			defer p.wg.Done()

			p.runPlugin(ctx, plug)
		}()
	}

	return nil
}

func (p *Probe) createReporter() {
	// Once the reporter is created successfully, the network abnormalities of the reporter itself
	// need to be maintained by the reporter itself.

	cfgs := config.Cfg.Reporters

	p.wg.Add(1)
	go func() {
		defer p.wg.Done()

		for {
			select {
			case <-p.quit:
				return

			default:

				var failedCfgs []config.ReporterConfig

				for _, cfg := range cfgs {
					r, err := reporter.NewReporter(cfg)
					if err != nil {
						logger.Warn("create new reporter failed, reporter(%s), %v", cfg.Name, err)
						failedCfgs = append(failedCfgs, cfg)
						continue
					}

					p.reporters = append(p.reporters, r)
				}

				if len(failedCfgs) == 0 {
					logger.Info("created all reporter successfully, reporter count(%d)", len(p.reporters))
					return
				}

				cfgs = failedCfgs
				failedCfgs = make([]config.ReporterConfig, 0)

				time.Sleep(100 * time.Millisecond)
			}
		}
	}()
}

func (p *Probe) Run(ctx context.Context) error {
	p.quit = make(chan struct{})

	if err := p.loadPlugins(ctx); err != nil {
		return err
	}

	p.createReporter()

	// event loop
	for {
		select {
		case <-p.quit:
			return nil

		default:
			// Avoid having all goroutines asleep.
			time.Sleep(1 * time.Second)
		}
	}
}

func (p *Probe) Close() {
	if p.quit != nil {
		close(p.quit) // Notify all goroutines exited.
	}
}
