/**
 * MIT License *
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
	"os"
	"strings"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/spf13/cobra"
)

// shouldRemovePidFileOnShutdown reports whether the worker should delete the pid
// file on shutdown. Workers started under a guard never write the pid file and
// must not remove the guard-owned file.
func shouldRemovePidFileOnShutdown(pidFile string) bool {
	return pidFile != "" && os.Getenv(process.EnvUnderGuard) == ""
}

func setupGracefulShutdown(p *Probe) error {
	// waiter delivers shutdown/reload notifications: POSIX signals on Unix
	// (SIGINT/SIGTERM shutdown, SIGHUP reload), the named stop/reload events on
	// Windows. Reload is applied by the probe reload worker.
	waiter, err := process.NewStopWaiter(process.EventKeyFromPidFile(p.pidFile))
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "setup stop waiter failed, errmsg: %s", err)
	}

	if err := process.SavePid(p.pidFile); err != nil {
		waiter.Close()
		return gerrors.Newf(gerrors.Failure, "save pid failed, errmsg: %s", err)
	}

	go func() {
		for {
			select {
			case <-waiter.Reload:
				logger.Info("received reload request, reloading configuration...")
				select {
				case p.reloadC <- struct{}{}:
				default:
				}
			case <-waiter.Shutdown:
				logger.Info("shutdown probe")
				p.Close()

				if shouldRemovePidFileOnShutdown(p.pidFile) {
					_ = os.Remove(p.pidFile)
				}
				os.Exit(0)
			}
		}
	}()
	return nil
}

// Run loads the probe config from ConfigFilePath, installs the logger, writes
// the pid file, and blocks in Probe.Run until a shutdown signal.
// It returns a non-nil error when config load, machine-id generation, or
// graceful-shutdown setup fails. On a successful shutdown the process exits
// from the signal goroutine rather than returning from Run.
func Run(cmd *cobra.Command, args []string) error {
	if err := config.Load(ConfigFilePath); err != nil {
		return err
	}

	logCfg := logger.Config{
		FileName:   config.Cfg.Log.Path,
		LogLevel:   logger.Level(config.Cfg.Log.Level),
		MaxSizeMB:  config.Cfg.Log.FileSize,
		MaxBackups: config.Cfg.Log.FileCount,
	}

	log := logger.NewDbmLogger(logCfg)
	logger.SetLogger(log)

	logger.Debug("probe startup config, log_path: %s, log_level: %s",
		config.Cfg.Log.Path, config.Cfg.Log.Level)

	if err := logProbeProviderSelfCheck(); err != nil {
		return err
	}

	clientID, err := machine.ID()
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "generate machine-id failed, %v", err)
	}

	ctx := context.Background()
	p := newProbe(ctx, clientID)

	if err := setupGracefulShutdown(p); err != nil {
		return err
	}

	return p.Run(ctx)
}

func logProbeProviderSelfCheck() error {
	entries := harvester.Entries()
	blockNames := make([]string, 0, len(entries))
	for _, e := range entries {
		blockNames = append(blockNames, e.BlockName)
	}
	logger.Info(
		"probe provider self-check, registered_db_types: %s, provider_owned_db_types: %s, "+
			"harvester_blocks: %s, endpoint_router_db_types: %s",
		joinDbTypes(dbtype.RegisteredDbTypes()),
		joinDbTypes(dbtype.ProviderOwnedDbTypes()),
		strings.Join(blockNames, ","),
		joinDbTypes(dbtype.EndpointRouterDbTypes()),
	)
	if len(entries) == 0 {
		return gerrors.Newf(gerrors.Failure, "no harvester plugins registered; blank-import provider/allprobe")
	}
	return nil
}

func joinDbTypes(types []haprobe.DbType) string {
	if len(types) == 0 {
		return ""
	}
	parts := make([]string, 0, len(types))
	for _, dt := range types {
		parts = append(parts, string(dt))
	}
	return strings.Join(parts, ",")
}
