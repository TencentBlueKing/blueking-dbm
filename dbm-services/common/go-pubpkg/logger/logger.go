/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package logger package
package logger

import (
	"fmt"
	"io"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// Field TODO
type Field = zap.Field

// Logger TODO
type Logger struct {
	Zap      *zap.Logger
	EmptyZap *zap.Logger
	Level    Level
	Fields   []zap.Field
}

// Debug TODO
func (l *Logger) Debug(format string, args ...interface{}) {
	l.Zap.Debug(fmt.Sprintf(format, args...), l.Fields...)
}

// Info TODO
func (l *Logger) Info(format string, args ...interface{}) {
	l.Zap.Info(fmt.Sprintf(format, args...), l.Fields...)
}

// Warn TODO
func (l *Logger) Warn(format string, args ...interface{}) {
	l.Zap.Warn(fmt.Sprintf(format, args...), l.Fields...)
}

// Error 用于错误处理
func (l *Logger) Error(format string, args ...interface{}) {
	l.Zap.Error(fmt.Sprintf(format, args...), l.Fields...)
}

// DPanic TODO
func (l *Logger) DPanic(format string, args ...interface{}) {
	l.Zap.DPanic(fmt.Sprintf(format, args...), l.Fields...)
}

// Panic TODO
func (l *Logger) Panic(format string, args ...interface{}) {
	l.Zap.Panic(fmt.Sprintf(format, args...), l.Fields...)
}

// Fatal TODO
func (l *Logger) Fatal(format string, args ...interface{}) {
	l.Zap.Fatal(fmt.Sprintf(format, args...), l.Fields...)
}

// With TODO
func (l *Logger) With(fields ...Field) *Logger {
	logger := l.Zap.With(fields...)
	l.Zap = logger
	return l
}

// Local TODO
func (l *Logger) Local(format string, args ...interface{}) {
	l.EmptyZap.Info(fmt.Sprintf(format, args...))
}

// Sync TODO
func (l *Logger) Sync() error {
	return l.Zap.Sync()
}

// GetLogger TODO
func GetLogger() *zap.Logger {
	return zap.L()
}

// New logger
// @receiver writer
// @receiver format 是否格式化日志
// @receiver level
// @receiver extMap
// @return *Logger
func New(writer io.Writer, format bool, level Level, extMap ...map[string]string) *Logger {
	if writer == nil {
		panic("the writer is nil")
	}

	cfg := zap.NewProductionConfig()
	cfg.EncoderConfig = zapcore.EncoderConfig{
		MessageKey:     "msg",
		LevelKey:       "levelname",
		TimeKey:        "time",
		NameKey:        "name",
		FunctionKey:    "funcName",
		StacktraceKey:  "stacktrace",
		CallerKey:      "caller",
		SkipLineEnding: false,
		LineEnding:     zapcore.DefaultLineEnding,
		EncodeLevel:    zapcore.LowercaseLevelEncoder,
		EncodeTime:     zapcore.RFC3339TimeEncoder,
		EncodeDuration: zapcore.SecondsDurationEncoder,
		EncodeName:     zapcore.FullNameEncoder,
		EncodeCaller:   zapcore.ShortCallerEncoder,
	}

	encoder := NewConsoleEncoder(cfg.EncoderConfig)
	if format {
		encoder = NewEncoder(cfg.EncoderConfig)
	}
	core := zapcore.NewCore(
		encoder,
		zapcore.AddSync(writer),
		level,
	)
	logger := &Logger{
		EmptyZap: zap.New(core),
		Zap:      zap.New(core),
		Level:    level,
	}

	// 初始化默认字段
	fs := make([]zap.Field, 0)
	for _, ext := range extMap {
		for key, value := range ext {
			fs = append(fs, zap.String(key, value))
		}
	}
	logger = logger.With(fs...)
	return logger
}
