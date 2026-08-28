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
	"errors"
	"fmt"
	"math/rand/v2"
	"reflect"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/configsync"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/proto"
)

const (
	// syncJitterDivisor sets the jitter added to each interval to a tenth of it.
	syncJitterDivisor = 10

	// maxStartupDelay caps how long the first sync is held back to spread a fleet restart.
	maxStartupDelay = 30 * time.Second

	// syncPullTimeout bounds one round of fetching from admin. The effective timeout is also
	// capped by the sync interval, so a slow admin cannot make requests overlap.
	syncPullTimeout = 30 * time.Second

	// syncLockTimeout bounds the wait for the config file lock. Failing the round is fine: the
	// next tick retries, whereas waiting indefinitely would pin the goroutine on a stuck peer.
	syncLockTimeout = 10 * time.Second
)

// runAdminSync keeps the config file in step with what admin reports for this machine.
//
// Each round re-reads the settings through config.Snapshot, so turning sync on or off, or
// changing its interval, takes effect on the next round without restarting the probe. The
// goroutine therefore stays alive even while sync is disabled: exiting would make enabling it
// again require a restart.
func (p *Probe) runAdminSync() {
	if p.configPath == "" {
		logger.Warn("config path is empty, periodic admin config sync is disabled")
		return
	}

	// Hold the first round back by a random delay. A fleet restarted together would otherwise
	// query admin in one burst and, since every probe uses the same interval, stay aligned.
	if !p.waitStartupDelay() {
		return
	}

	for {
		admin := config.Snapshot().Admin
		if !admin.SyncEnabled() {
			if !p.sleepOrStop(config.MinSyncInterval) {
				return
			}
			continue
		}

		if !p.sleepOrStop(nextSyncDelay(admin.SyncInterval)) {
			return
		}

		// Re-read: the settings may have changed while this round was waiting.
		p.syncOnce(config.Snapshot().Admin)
	}
}

// syncOnce runs one fetch-and-reconcile round. Every failure is logged and swallowed, because
// a round that cannot complete must leave the running configuration exactly as it was; the next
// round retries.
func (p *Probe) syncOnce(admin config.AdminConfig) {
	if !admin.SyncEnabled() {
		return
	}

	payload, err := p.fetchRemoteConfig(admin)
	if err != nil {
		if errors.Is(err, configsync.ErrNoData) {
			// Admin answered, it just has nothing for this machine. Overwriting a working
			// config with an empty one would silently stop all collection here, so the
			// existing config stays and this is surfaced for an operator to look at.
			logger.Warn("admin has no metadata for this machine, keeping current config, ip: %s", admin.LocalIP)
			return
		}
		logger.Warn("fetch config from admin failed, errmsg: %s", err)
		return
	}

	changed, err := p.reconcileConfigFile(payload)
	if err != nil {
		logger.Warn("reconcile config file failed, config_path: %s, errmsg: %s", p.configPath, err)
		return
	}
	if !changed {
		return
	}

	logger.Info("config file updated from admin, config_path: %s", p.configPath)
	p.requestReload()
}

func (p *Probe) fetchRemoteConfig(admin config.AdminConfig) (probeconfig.ProbeConfigPayload, error) {
	timeout := syncPullTimeout
	if admin.SyncInterval > 0 && admin.SyncInterval < timeout {
		timeout = admin.SyncInterval
	}

	ctx, cancel := context.WithTimeout(p.parent, timeout)
	defer cancel()

	return configsync.Fetch(ctx, admin.Endpoints, &proto.ProbeConfigRequest{
		BkCloudId: admin.BkCloudID,
		Ip:        admin.LocalIP,
		ClientID:  p.clientID,
	})
}

// reconcileConfigFile brings the config file in line with what admin returned and reports
// whether it had to change anything.
//
// The read-render-compare-write sequence runs as a whole under the config file lock. Doing the
// read and the write as two separately locked steps would leave a gap in which a concurrent
// gen-config could land, and this path would then quietly revert it.
//
// The fetch deliberately happens outside the lock: holding it across a round-trip to admin
// would block gen-config for as long as admin takes to answer.
func (p *Probe) reconcileConfigFile(payload probeconfig.ProbeConfigPayload) (bool, error) {
	lockPath, err := process.LockPathFor(p.configPath)
	if err != nil {
		return false, fmt.Errorf("resolve config lock path: %w", err)
	}
	fl, err := process.AcquireFileLock(lockPath, syncLockTimeout)
	if err != nil {
		return false, fmt.Errorf("acquire config lock: %w", err)
	}
	defer func() { _ = fl.Unlock() }()

	disk, diskErr := config.Parse(p.configPath)

	// Locally owned fields are taken from the file, not from memory. An operator may have
	// edited the file and not reloaded yet; sourcing these from the applied config would
	// overwrite that edit as soon as the harvester section happens to change. Memory is used
	// only when the file cannot be parsed, which is the self-healing case handled below.
	local := disk
	if diskErr != nil {
		local = config.Snapshot()
	}

	rendered, err := configsync.Render(payload, config.LocalFields(local)...)
	if err != nil {
		return false, err
	}

	// Validate before overwriting anything. A rendering defect would otherwise replace a
	// working file with one the probe cannot parse, unattended and on every machine at once.
	// Keeping the old file turns that into a logged warning instead of an outage on restart.
	renderedCfg, err := config.ParseBytes([]byte(rendered))
	if err != nil {
		return false, fmt.Errorf("rendered config does not parse, keeping the current file: %w", err)
	}

	if diskErr != nil {
		logger.Warn("config file cannot be parsed, rewriting it from admin, config_path: %s, errmsg: %s",
			p.configPath, diskErr)
		return process.WriteFileLocked(p.configPath, []byte(rendered))
	}

	if configEquivalent(disk, renderedCfg) {
		return false, nil
	}

	return process.WriteFileLocked(p.configPath, []byte(rendered))
}

// configEquivalent compares the two sections periodic sync owns, reporter and harvester.
//
// Comparing rendered bytes against the file would instead report a difference for every comment
// and formatting choice in it, and rewriting would then erase them on the first sync. Comparing
// against the parsed file rather than the applied config also matters: the file is what the
// next reload reads, so converging on it is what makes repeated syncs settle.
func configEquivalent(disk, rendered config.Configuration) bool {
	return reflect.DeepEqual(disk.Reporter, rendered.Reporter) &&
		reflect.DeepEqual(disk.Harvester, rendered.Harvester)
}

// requestReload nudges the reload worker to pick up the new file.
//
// A full buffer means a reload is already queued, and dropping the signal is safe: the worker
// re-reads the file when it runs, so the pending reload will see this change as well.
func (p *Probe) requestReload() {
	select {
	case p.reloadC <- struct{}{}:
	default:
	}
}

// waitStartupDelay spreads the first round across the interval, capped at maxStartupDelay so a
// long interval does not postpone the first sync for hours.
func (p *Probe) waitStartupDelay() bool {
	admin := config.Snapshot().Admin
	if !admin.SyncEnabled() {
		return true
	}

	delay := maxStartupDelay
	if admin.SyncInterval < delay {
		delay = admin.SyncInterval
	}

	return p.sleepOrStop(randomDuration(delay))
}

// nextSyncDelay is the interval plus up to a tenth of it, so probes that started together drift
// apart instead of hitting admin in step forever.
func nextSyncDelay(interval time.Duration) time.Duration {
	jitter := interval / syncJitterDivisor
	if jitter <= 0 {
		return interval
	}

	return interval + randomDuration(jitter)
}

func randomDuration(limit time.Duration) time.Duration {
	if limit <= 0 {
		return 0
	}

	return time.Duration(rand.Int64N(int64(limit)))
}

// sleepOrStop waits for d and reports whether the caller should keep going; it returns false as
// soon as the probe starts shutting down.
func (p *Probe) sleepOrStop(d time.Duration) bool {
	timer := time.NewTimer(d)
	defer timer.Stop()

	select {
	case <-p.shutdown:
		return false
	case <-p.parent.Done():
		return false
	case <-timer.C:
		return true
	}
}
