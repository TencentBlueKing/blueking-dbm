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
	"reflect"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// runReloadWorker serializes hot-reload requests from the buffered reloadC channel.
func (p *Probe) runReloadWorker() {
	defer close(p.reloadWorkerDone)
	for {
		select {
		case <-p.shutdown:
			return
		case <-p.reloadC:
			p.reloadOnce(p.configPath)
		}
	}
}

// reloadOnce parses path and, when the reloadable view differs from the applied
// config, replaces the harvester generation and optionally the reporter.
func (p *Probe) reloadOnce(path string) {
	next, err := config.Parse(path)
	if err != nil {
		logger.Warn("parse probe config failed, config_path: %s, errmsg: %s", path, err)
		return
	}

	next = config.RetainIdentity(config.Cfg, next)

	// Skip when unchanged to avoid stop/quiesce/rebuild of an identical runtime.
	if reflect.DeepEqual(next, config.Cfg) {
		logger.Info("probe config unchanged, skip reload, config_path: %s", path)
		return
	}

	// The admin block only steers the periodic sync loop, which re-reads it from the applied
	// config on every round. Making it current is enough; tearing down the harvesters and the
	// reporter for it would interrupt collection to no effect.
	if onlyAdminChanged(config.Cfg, next) {
		config.Apply(next)
		logger.Info("probe admin settings updated without runtime rebuild, config_path: %s", path)
		return
	}

	p.applyReload(next, path)
}

// onlyAdminChanged reports whether next differs from the applied config in the admin block and
// nowhere else.
func onlyAdminChanged(current, next config.Configuration) bool {
	if reflect.DeepEqual(current.Admin, next.Admin) {
		return false
	}

	withoutAdmin := next
	withoutAdmin.Admin = current.Admin

	return reflect.DeepEqual(withoutAdmin, current)
}

func (p *Probe) applyReload(next config.Configuration, path string) {
	p.runtime.stop()
	p.reporter.quiesce()

	if p.parent.Err() != nil {
		logger.Info("probe shutting down, abandon reload apply, config_path: %s", path)
		return
	}

	// Client is consumed only when constructing a GRPC reporter; include it in the
	// rebuild decision so Client-only edits take effect without a process restart.
	rebuildReporter := !reporterConfigEqual(p.reporter.cfg, next.Reporter) ||
		!reflect.DeepEqual(config.Cfg.Client, next.Client)

	config.Apply(next)
	p.reporter.applyAfterReload(p.parent, next.Reporter, rebuildReporter)
	p.runtime = p.startRuntime(p.parent, next.ServiceID)
	logger.Info("probe config reloaded, config_path: %s", path)
}
