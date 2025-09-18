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
	dbmlogger "dbm-services/common/go-pubpkg/logger"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

type DbmLogger struct {
	dbmLogger *dbmlogger.Logger
}

func (z *DbmLogger) OriginLogger() *zap.Logger {
	return z.dbmLogger.Zap
}

func (z *DbmLogger) Debug(format string, args ...any) {
	z.dbmLogger.Debug(format, args...)
}

func (z *DbmLogger) Info(format string, args ...any) {
	z.dbmLogger.Info(format, args...)
}

func (z *DbmLogger) Warn(format string, args ...any) {
	z.dbmLogger.Warn(format, args...)
}

func (z *DbmLogger) Error(format string, args ...any) {
	z.dbmLogger.Error(format, args...)
}

func (z *DbmLogger) Fatal(format string, args ...any) {
	z.dbmLogger.Fatal(format, args...)
}

func (z *DbmLogger) Sync() error {
	return z.dbmLogger.Sync()
}

// NewDbmLogger Create a logger with DBM log library.
func NewDbmLogger(config Config) Logger {
	opts := []dbmlogger.TreeOption{
		{
			FileName: config.FileName,
			Rpt: dbmlogger.RotateOptions{
				MaxSize:    config.MaxSizeMB,
				MaxBackups: config.MaxBackups,
				MaxAge:     config.MaxAge,
				Compress:   true,
			},

			Lef: func(level zapcore.Level) bool {
				return level >= convertLevel(config.LogLevel)
			},
		},
	}

	lg := dbmlogger.NewRotate(opts)
	dbmlogger.ResetDefault(lg)

	return &DbmLogger{dbmLogger: lg}
}
