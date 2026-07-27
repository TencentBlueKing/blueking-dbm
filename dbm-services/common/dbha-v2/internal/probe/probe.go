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

// Package probe implements the probe main framework for harvesting and reporting DB instance data.
package probe

import (
	"context"
	"encoding/json"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/client"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// Probe probe main framework
type Probe struct {
	clientID  string
	machineID string
	serviceID string
	reporter  client.Reporter
	quit      chan struct{}
	wg        sync.WaitGroup
}

func (p *Probe) runPlugin(ctx context.Context, plug plugin.Plugin) {
	name, _ := plug.Name()

	defer func() {
		if err := plug.Close(); err != nil {
			logger.Error("exit harvester plugin failed, plugin: %s, errmsg: %s", name, err)
		}
	}()

	eventC, err := plug.Harvest(ctx, p.machineID, p.serviceID)
	if err != nil {
		logger.Warn("start harvester plugin failed, plugin: %s, errmsg: %s", name, err)
		return
	}

	for {
		select {
		case <-p.quit:
			return

		case <-ctx.Done():
			return

		case data, opened := <-eventC:
			if !opened {
				logger.Error("the event chan is closed, exit from the plugin: %s", name)
				return
			}

			baseInfo := p.reporter.GetBaseInfo()

			data.AgentID = baseInfo.AgentID
			data.BkCloudID = baseInfo.BkCloudID
			data.DbTypeName = data.Value.GetDbType()

			dataEncoded, err := json.Marshal(data)
			if err != nil {
				logger.Warn("encode data to json failed, plugin: %s, data: %v, errmsg: %s", name, data.Value, err)
				continue
			}

			logger.Debug("harvester reported data: %s", string(dataEncoded))

			if p.reporter != nil {
				if err := p.reporter.Post(ctx, dataEncoded); err != nil {
					logger.Warn("post data to receiver failed, plugin: %s, reporter: %s, errmsg: %s",
						name, p.reporter.Name(), err)
				}
			}
		}
	}
}

// startPlugin creates a plugin via factory and runs it in a goroutine.
// A factory may return (nil, nil) to signal that the plugin is not configured
// (e.g. probe yaml omits the corresponding harvester block); in that case startPlugin
// silently skips so we never run a plugin with a nil cfg.
func (p *Probe) startPlugin(ctx context.Context, dbType string, factory pluginFactory) {
	plug, err := factory()
	if err != nil {
		logger.Warn("failed to create a new harvester, dbType: %s, errmsg: %s", dbType, err)
		return
	}
	if plug == nil {
		logger.Info("harvester not configured, skip, dbType: %s", dbType)
		return
	}
	p.wg.Add(1)
	go func() {
		defer p.wg.Done()
		p.runPlugin(ctx, plug)
	}()
}

func (p *Probe) loadPlugins(ctx context.Context) error {
	for _, e := range effectivePluginEntries() {
		p.startPlugin(ctx, e.name, e.factory)
	}
	return nil
}

func (p *Probe) createReporter() {
	// Once the reporter is created successfully, the network abnormalities of the reporter itself
	// need to be maintained by the reporter itself.

	if config.Cfg.Reporter == nil {
		return
	}

	cfg := *config.Cfg.Reporter
	p.wg.Add(1)
	go func() {
		defer p.wg.Done()

		for {
			select {
			case <-p.quit:
				return

			default:
				r, err := client.NewReporter(cfg)
				if err != nil {
					logger.Warn("create new reporter failed, reporter: %s, errmsg: %s", cfg.Name, err)
					time.Sleep(100 * time.Millisecond)
					continue
				}

				p.reporter = r
				logger.Info("created reporter successfully, reporter(%s)", cfg.Name)
				return
			}
		}
	}()
}

// Run starts the probe: loads plugins, creates the reporter, and runs the event loop until quit.
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

// Close signals the probe to stop and waits for goroutines to exit.
func (p *Probe) Close() {
	if p.quit != nil {
		close(p.quit) // Notify all goroutines exited.
	}
}
