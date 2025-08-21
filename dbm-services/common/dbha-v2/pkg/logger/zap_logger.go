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

package logger

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

type ZapLogger struct {
	logger        *zap.Logger
	sugaredLogger *zap.SugaredLogger
}

func (z *ZapLogger) OriginLogger() *zap.Logger {
	return z.logger
}

func (z *ZapLogger) Debug(format string, args ...interface{}) {
	z.sugaredLogger.Debugf(format, args...)
}

func (z *ZapLogger) Info(format string, args ...interface{}) {
	z.sugaredLogger.Infof(format, args...)
}

func (z *ZapLogger) Warn(format string, args ...interface{}) {
	z.sugaredLogger.Warnf(format, args...)
}

func (z *ZapLogger) Error(format string, args ...interface{}) {
	z.sugaredLogger.Errorf(format, args...)
}

func (z *ZapLogger) Fatal(format string, args ...interface{}) {
	z.sugaredLogger.Fatalf(format, args...)
}

func (z *ZapLogger) Sync() error {
	return z.logger.Sync()
}

func convertLevel(level Level) zapcore.Level {
	switch level {
	case DebugLevel:
		return zapcore.DebugLevel
	case InfoLevel:
		return zapcore.InfoLevel
	case ErrorLevel:
		return zapcore.ErrorLevel
	case FatalLevel:
		return zapcore.FatalLevel
	default:
		return zapcore.InfoLevel
	}
}

// NewZapLogger create a zap logger
func NewZapLogger(config Config) Logger {

	logRotator := &lumberjack.Logger{
		Filename:   config.FileName,
		MaxSize:    config.MaxSizeMB,
		MaxBackups: config.MaxBackups,
		MaxAge:     config.MaxAge,
		Compress:   true,
	}

	cfg := zap.NewProductionConfig()
	cfg.EncoderConfig = zapcore.EncoderConfig{
		MessageKey:     "msg",
		LevelKey:       "levelName",
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

	encoder := zapcore.NewConsoleEncoder(cfg.EncoderConfig)
	core := zapcore.NewCore(encoder, zapcore.AddSync(logRotator), convertLevel(config.LogLevel))
	logger := zap.New(core, zap.AddCaller(), zap.AddCallerSkip(2))

	return &ZapLogger{logger: logger, sugaredLogger: logger.Sugar()}
}
