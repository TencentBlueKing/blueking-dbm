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

// Probe is the main harvest/report framework. Lifecycle fields (parent, shutdown,
// reloadC) are initialized by newProbe before setupGracefulShutdown so early
// signals never observe nil channels or cancel funcs.
type Probe struct {
	clientID         string
	machineID        string
	pidFile          string
	parent           context.Context
	runCancel        context.CancelFunc
	shutdown         chan struct{}
	shutdownOnce     sync.Once
	reloadC          chan struct{}
	reloadWorkerDone chan struct{}
	runtime          *harvestRuntime
	reporter         *reporterUnit
	configPath       string
}

// newProbe builds a Probe with all lifecycle fields ready for signal handling.
// pidFile is snapshotted from config.Cfg so the shutdown path never races with
// hot-reload writes to the package-level configuration.
func newProbe(ctx context.Context, clientID string) *Probe {
	parent, runCancel := context.WithCancel(ctx)
	return &Probe{
		clientID:         clientID,
		machineID:        clientID,
		pidFile:          config.Cfg.PidFile,
		parent:           parent,
		runCancel:        runCancel,
		shutdown:         make(chan struct{}),
		reloadC:          make(chan struct{}, 1),
		reloadWorkerDone: make(chan struct{}),
		reporter:         &reporterUnit{},
		configPath:       ConfigFilePath,
	}
}

// Run starts harvest plugins and the reporter, then blocks until Close signals
// shutdown. The context argument is unused; cancelation uses p.parent which was
// set by newProbe before signal listening began.
func (p *Probe) Run(ctx context.Context) error {
	_ = ctx
	p.runtime = p.startRuntime(p.parent, config.Cfg.ServiceID)
	p.reporter.start(p.parent, config.Cfg.Reporter)
	go p.runReloadWorker()
	go p.runAdminSync()
	<-p.shutdown
	return nil
}

// Close signals the probe to stop. It does not wait for harvester or reporter
// goroutines; the shutdown path in setupGracefulShutdown exits the process after
// Close returns.
func (p *Probe) Close() {
	p.shutdownOnce.Do(func() {
		if p.runCancel != nil {
			p.runCancel()
		}
		if p.shutdown != nil {
			close(p.shutdown)
		}
	})
}

func (p *Probe) runPlugin(ctx context.Context, plug plugin.Plugin, serviceID string) {
	name, _ := plug.Name()

	defer func() {
		if err := plug.Close(); err != nil {
			logger.Error("exit harvester plugin failed, plugin: %s, errmsg: %s", name, err)
		}
	}()

	eventC, err := plug.Harvest(ctx, p.machineID, serviceID)
	if err != nil {
		logger.Warn("start harvester plugin failed, plugin: %s, errmsg: %s", name, err)
		return
	}

	for {
		select {
		case <-ctx.Done():
			return

		case data, opened := <-eventC:
			if !opened {
				logger.Error("the event chan is closed, exit from the plugin: %s", name)
				return
			}

			rep := p.reporter.get()
			if rep == nil {
				continue
			}

			baseInfo := rep.GetBaseInfo()
			data.AgentID = baseInfo.AgentID
			data.BkCloudID = baseInfo.BkCloudID
			data.DbTypeName = data.Value.GetDbType()

			dataEncoded, err := json.Marshal(data)
			if err != nil {
				logger.Warn("encode data to json failed, plugin: %s, data: %v, errmsg: %s",
					name, data.Value, err)
				continue
			}

			logger.Debug("harvester reported data: %s", string(dataEncoded))

			if err := rep.Post(ctx, dataEncoded); err != nil {
				logger.Warn("post data to receiver failed, plugin: %s, reporter: %s, errmsg: %s",
					name, rep.Name(), err)
			}
		}
	}
}

// startPlugin creates a plugin via factory and runs it under rt.
// A factory may return (nil, nil) to signal that the plugin is not configured
// (e.g. probe yaml omits the corresponding harvester block); in that case
// startPlugin silently skips so we never run a plugin with a nil cfg.
func (p *Probe) startPlugin(
	ctx context.Context, rt *harvestRuntime, dbType string, factory pluginFactory, serviceID string,
) {
	plug, err := factory()
	if err != nil {
		logger.Warn("failed to create a new harvester, dbType: %s, errmsg: %s", dbType, err)
		return
	}
	if plug == nil {
		logger.Info("harvester not configured, skip, dbType: %s", dbType)
		return
	}
	rt.wg.Add(1)
	go func() {
		defer rt.wg.Done()
		p.runPlugin(ctx, plug, serviceID)
	}()
}

func (p *Probe) startRuntime(parent context.Context, serviceID string) *harvestRuntime {
	ctx, cancel := context.WithCancel(parent)
	rt := &harvestRuntime{cancel: cancel}
	for _, e := range pluginEntries {
		p.startPlugin(ctx, rt, e.name, e.factory, serviceID)
	}
	return rt
}

// harvestRuntime owns one generation of harvester plugins.
type harvestRuntime struct {
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

func (rt *harvestRuntime) stop() {
	if rt == nil {
		return
	}
	if rt.cancel != nil {
		rt.cancel()
	}
	rt.wg.Wait()
}

// reporterUnit owns the reporter create/retry goroutine and the live Reporter
// instance across harvester generations.
type reporterUnit struct {
	cfg      *config.ReporterConfig
	cancel   context.CancelFunc
	wg       sync.WaitGroup
	reporter client.Reporter
	mu       sync.Mutex
}

func (u *reporterUnit) get() client.Reporter {
	u.mu.Lock()
	defer u.mu.Unlock()
	return u.reporter
}

// quiesce cancels the create/retry goroutine and waits for it to exit without
// closing an already-created Reporter instance.
func (u *reporterUnit) quiesce() {
	if u == nil {
		return
	}
	if u.cancel != nil {
		u.cancel()
		u.cancel = nil
	}
	u.wg.Wait()
}

// start launches (or clears) the reporter. When cfg is nil the live instance is
// set to nil so runPlugin skips events instead of nil-panicking in GetBaseInfo.
func (u *reporterUnit) start(parent context.Context, cfg *config.ReporterConfig) {
	u.cfg = cfg
	if cfg == nil {
		u.mu.Lock()
		u.reporter = nil
		u.mu.Unlock()
		return
	}

	copied := *cfg
	ctx, cancel := context.WithCancel(parent)
	u.cancel = cancel
	u.wg.Add(1)
	go func() {
		defer u.wg.Done()
		u.createLoop(ctx, copied)
	}()
}

func (u *reporterUnit) createLoop(ctx context.Context, cfg config.ReporterConfig) {
	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		r, err := client.NewReporter(cfg)
		if err != nil {
			logger.Warn("create new reporter failed, reporter: %s, errmsg: %s", cfg.Name, err)
			select {
			case <-ctx.Done():
				return
			case <-time.After(100 * time.Millisecond):
				continue
			}
		}

		u.mu.Lock()
		if ctx.Err() != nil {
			u.mu.Unlock()
			r.Close()
			return
		}
		u.reporter = r
		u.mu.Unlock()
		logger.Info("created reporter successfully, reporter: %s", cfg.Name)
		return
	}
}

// applyAfterReload closes the previous reporter when rebuild is true, then
// starts a new create loop (or clears the instance when cfg is nil). When
// rebuild is false and an instance is already live, the instance is left alone;
// if the instance is still nil (create was interrupted by quiesce), create is
// restarted with a fresh context.
func (u *reporterUnit) applyAfterReload(
	parent context.Context, next *config.ReporterConfig, rebuild bool,
) {
	if !rebuild {
		if u.get() != nil {
			return
		}
		u.start(parent, next)
		return
	}

	u.mu.Lock()
	old := u.reporter
	u.reporter = nil
	u.mu.Unlock()
	if old != nil {
		old.Close()
	}
	u.start(parent, next)
}

func reporterConfigEqual(a, b *config.ReporterConfig) bool {
	if a == nil && b == nil {
		return true
	}
	if a == nil || b == nil {
		return false
	}
	return *a == *b
}
