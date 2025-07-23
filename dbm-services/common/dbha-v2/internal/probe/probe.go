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
	*reporter.Reporter
	plugins []plugin.Plugin
	quit    chan struct{}
	wg      sync.WaitGroup
}

func (p *Probe) runPlugin(ctx context.Context, plug plugin.Plugin) {
	name, _ := plug.Name()

	defer func() {
		if err := plug.Close(); err != nil {
			logger.Error("exit harvester plugin(%s) failed, errmsg(%v)", name, err)
		}
	}()

	eventC, err := plug.Harvest(ctx)
	if err != nil {
		logger.Warn("start harvester plugin(%s) failed, errmsg(%v)", name, err)
		return
	}

	for {
		select {
		case <-p.quit:
			return

		case <-ctx.Done():
			return

		case data := <-eventC:
			dataEncoded, err := json.Marshal(data)
			if err != nil {
				logger.Warn("encode data to json failed, plugin(%s), errmsg(%v)", name, err)
				continue
			}
			if err := p.Reporter.PostToReceiver(dataEncoded); err != nil {
				logger.Warn("post data to receiver failed, plugin(%s), errmsg(%v)", name, err)
			}
		}
	}
}

func (p *Probe) loadPlugins(ctx context.Context) error {
	if p.plugins == nil {
		p.plugins = make([]plugin.Plugin, 20)
	}

	for _, cfg := range config.Cfg.Harvester {
		plug, err := harvester.NewPlugin(cfg)
		if err != nil {
			logger.Warn("create a new harvester plugin(%s) failed, errmsg(%v)", cfg.Name, err)
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

func (p *Probe) Run(ctx context.Context) error {
	p.quit = make(chan struct{})

	if err := p.Reporter.CreateClients(ctx); err != nil {
		return err
	}

	if err := p.loadPlugins(ctx); err != nil {
		return err
	}

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
