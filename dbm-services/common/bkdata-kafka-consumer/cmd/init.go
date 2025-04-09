// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package cmd

import (
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/natefinch/lumberjack"
	"github.com/spf13/viper"

	"dbm-services/common/bkdata-kafka-consumer/pkg/config"
)

var executable string
var executableName string
var executableDir string

func init() {
	executable, _ = os.Executable()
	executableName = filepath.Base(executable)
	executableDir = filepath.Dir(executable)

	rootCmd.PersistentFlags().StringP("config", "c", "", "runtime config file")
	_ = rootCmd.MarkPersistentFlagRequired("config")
	_ = viper.BindPFlag("config", rootCmd.PersistentFlags().Lookup("config"))
}

func initLogger(cfg *config.LogConfig) {
	var ioWriters []io.Writer

	if cfg.Console {
		ioWriters = append(ioWriters, os.Stdout)
	}

	if cfg.LogFileDir != nil {
		if !filepath.IsAbs(*cfg.LogFileDir) {
			*cfg.LogFileDir = filepath.Join(executableDir, *cfg.LogFileDir)
		}

		err := os.MkdirAll(*cfg.LogFileDir, 0755)
		if err != nil {
			panic(err)
		}

		// ToDo 修改目录宿主

		logFile := filepath.Join(*cfg.LogFileDir, fmt.Sprintf("%s.log", executableName))
		_, err = os.Stat(logFile)
		if err != nil {
			if os.IsNotExist(err) {
				_, err := os.Create(logFile)
				if err != nil {
					panic(err)
				}
				// ToDo 修改日志文件宿主
			} else {
				panic(err)
			}
		}

		ioWriters = append(ioWriters, &lumberjack.Logger{Filename: logFile})
	}

	handleOpt := slog.HandlerOptions{AddSource: cfg.Source}
	if cfg.Debug {
		handleOpt.Level = slog.LevelDebug
	} else {
		handleOpt.Level = slog.LevelInfo
	}

	var logger *slog.Logger
	if cfg.Json {
		logger = slog.New(slog.NewJSONHandler(io.MultiWriter(ioWriters...), &handleOpt))
	} else {
		logger = slog.New(slog.NewTextHandler(io.MultiWriter(ioWriters...), &handleOpt))
	}

	slog.SetDefault(logger)
}
