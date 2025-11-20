/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

// Package logger 日志处理模块
package logger

import (
	"fmt"
	commutil "k8s-dbs/common/util"
	"log"
	"os"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

const LogDir = "./logs/"
const LogFileName = "api.log"
const DefaultMaxSizeMB = 10
const DefaultMaxBackups = 5
const DefaultMaxAge = 30
const DefaultCompress = false

// InitLogger 初始化 Logger（zap+lumberjack）
func InitLogger() *zap.Logger {
	// 日志目录处理，不存在则创建
	if err := os.MkdirAll(LogDir, os.ModePerm); err != nil {
		log.Fatal("Failed to create log directory", zap.String("path", LogDir), zap.Error(err))
	}

	// 配置 Lumberjack（文件输出 + 滚动）
	lumberJackLogger := &lumberjack.Logger{
		Filename:   fmt.Sprintf("%s/%s", LogDir, LogFileName),
		MaxSize:    commutil.GetEnvAsInt("LOG_MAX_SIZE_MB", DefaultMaxSizeMB), // MB
		MaxBackups: commutil.GetEnvAsInt("LOG_MAX_BACKUPS", DefaultMaxBackups),
		MaxAge:     commutil.GetEnvAsInt("LOG_MAX_AGE", DefaultMaxAge),     // days
		Compress:   commutil.GetEnvAsBool("LOG_COMPRESS", DefaultCompress), // .gz
	}

	// ZapEncoder 配置
	encoderConfig := zapcore.EncoderConfig{
		TimeKey:        "time",
		LevelKey:       "level",
		NameKey:        "logger",
		CallerKey:      "caller",
		MessageKey:     "msg",
		StacktraceKey:  "stacktrace",
		LineEnding:     zapcore.DefaultLineEnding,
		EncodeLevel:    zapcore.LowercaseLevelEncoder,
		EncodeTime:     zapcore.ISO8601TimeEncoder,
		EncodeDuration: zapcore.StringDurationEncoder,
		EncodeCaller:   zapcore.ShortCallerEncoder,
	}

	// Zap Core
	core := zapcore.NewCore(
		zapcore.NewJSONEncoder(encoderConfig),
		zapcore.AddSync(lumberJackLogger),
		zapcore.InfoLevel,
	)

	// 带调用者信息的 Logger
	zapLogger := zap.New(core, zap.AddCaller())
	return zapLogger
}
