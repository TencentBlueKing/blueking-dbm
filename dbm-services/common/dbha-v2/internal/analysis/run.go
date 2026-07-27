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
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/internal/analysis/workflow/parser"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/process"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

func setupGracefulShutdown(svr *Service) {
	sigC := make(chan os.Signal, 1)
	signal.Notify(sigC, syscall.SIGINT, syscall.SIGTERM, syscall.SIGHUP)

	process.SavePid(config.Cfg.PidFile)

	go func() {
		for sig := range sigC {
			if sig == syscall.SIGHUP {
				logger.Info("received SIGHUP, reloading configuration...")
				continue
			}

			// SIGINT or SIGTERM: graceful shutdown
			logger.Info("shutdown analysis server")
			svr.Close()

			if config.Cfg.PidFile != "" {
				_ = os.Remove(config.Cfg.PidFile)
			}
			os.Exit(0)
		}
	}()
}

// Run run analysis service
func Run(cmd *cobra.Command, args []string) error {
	viper.SetConfigName("analysis")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./etc")

	if ConfigFilePath != "" {
		viper.SetConfigFile(ConfigFilePath)
	}

	if err := viper.ReadInConfig(); err != nil {
		return err
	}

	if err := viper.Unmarshal(&config.Cfg); err != nil {
		return err
	}

	// set a logger for DBHA
	logCfg := logger.Config{
		FileName:   config.Cfg.Log.Path,
		LogLevel:   logger.Level(config.Cfg.Log.Level),
		MaxSizeMB:  config.Cfg.Log.FileSize,
		MaxBackups: config.Cfg.Log.FileCount,
	}

	log := logger.NewDbmLogger(logCfg)
	logger.SetLogger(log)

	logBasename := filepath.Base(config.Cfg.Log.Path)
	logDir := filepath.Dir(config.Cfg.Log.Path)

	// create a logger for Etcd
	etcdLogCfg := logCfg
	etcdLogCfg.FileName = filepath.Join(logDir, "etcd-"+logBasename)

	etcdLogger := logger.NewZapLogger(etcdLogCfg)

	// create a logger for GORM
	gormLogCfg := logCfg
	gormLogCfg.FileName = filepath.Join(logDir, "gorm-"+logBasename)

	gormLogger := logger.NewZapLogger(gormLogCfg)

	// switching snapshot lines: SwitchID + JSON payload (same rotation as main log)
	snapshotLogCfg := logCfg
	snapshotLogCfg.FileName = filepath.Join(logDir, "switching-snapshot-"+logBasename)
	snapshotLogger := logger.NewZapLogger(snapshotLogCfg)

	logger.Debug("analysis startup config, log_path: %s, log_level: %s", config.Cfg.Log.Path, config.Cfg.Log.Level)

	if err := logAnalysisProviderSelfCheck(); err != nil {
		return err
	}

	ctx := context.Background()
	svr := &Service{etcdLogger: etcdLogger.OriginLogger(), gormLogger: gormLogger, swSnapshotLogger: snapshotLogger}

	setupGracefulShutdown(svr)

	return svr.Run(ctx)
}

func logAnalysisProviderSelfCheck() error {
	switcherTypes := switcher.RegisteredDbTypes()
	logger.Info(
		"analysis provider self-check, registered_db_types: %s, provider_owned_db_types: %s, "+
			"switcher_db_types: %s, parser_db_types: %s",
		joinDbTypes(dbtype.RegisteredDbTypes()),
		joinDbTypes(dbtype.ProviderOwnedDbTypes()),
		joinDbTypes(switcherTypes),
		joinDbTypes(parser.RegisteredDbTypes()),
	)
	if len(switcherTypes) == 0 {
		return gerrors.Newf(gerrors.Failure, "no switchers registered; blank-import provider/allanalysis")
	}
	if err := switcher.Validate(); err != nil {
		return gerrors.Newf(gerrors.Failure, "switcher validation failed, errmsg: %s", err)
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
