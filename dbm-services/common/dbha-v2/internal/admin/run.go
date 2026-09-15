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

package admin

import (
	"context"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/process"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

func setupGracefulShutdown(svr *Service) {
	sigC := make(chan os.Signal, 1)
	signal.Notify(sigC, syscall.SIGINT, syscall.SIGTERM, syscall.SIGHUP)

	process.SavePid(svr.pidFile)

	go func() {
		for sig := range sigC {
			if sig == syscall.SIGHUP {
				logger.Info("received SIGHUP, reloading configuration...")
				svr.requestReload()
				continue
			}

			logger.Info("shutdown admin server")
			svr.Close()

			if svr.pidFile != "" {
				_ = os.Remove(svr.pidFile)
			}
			os.Exit(0)
		}
	}()
}

// Run run admin service
func Run(cmd *cobra.Command, args []string) error {
	viper.SetConfigName("admin")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./etc")

	if ConfigFilePath != "" {
		viper.SetConfigFile(ConfigFilePath)
	}

	if err := viper.ReadInConfig(); err != nil {
		return err
	}

	// Preserve historical startup semantics: Unmarshal into a local copy (no clamp)
	// then publish via Apply. Reload uses Parse (with clamp) + Validate instead.
	next := config.Cfg
	if err := viper.Unmarshal(&next); err != nil {
		return err
	}
	config.Apply(next)

	configPath := viper.ConfigFileUsed()
	if abs, err := filepath.Abs(configPath); err == nil {
		configPath = abs
	}

	logCfg := logger.Config{
		FileName:   next.Log.Path,
		LogLevel:   logger.Level(next.Log.Level),
		MaxSizeMB:  next.Log.FileSize,
		MaxBackups: next.Log.FileCount,
	}

	log := logger.NewDbmLogger(logCfg)
	logger.SetLogger(log)

	logger.Debug("admin startup config, log_path: %s, log_level: %s", next.Log.Path, next.Log.Level)

	ctx := context.Background()
	svr := &Service{
		logger:           log.OriginLogger(),
		gormLogger:       log,
		runtimeLogger:    log,
		configPath:       configPath,
		pidFile:          next.PidFile,
		reloadC:          make(chan struct{}, 1),
		reloadWorkerDone: make(chan struct{}),
		shutdown:         make(chan struct{}),
	}

	setupGracefulShutdown(svr)
	go svr.runReloadWorker()

	return svr.Run(ctx)
}
