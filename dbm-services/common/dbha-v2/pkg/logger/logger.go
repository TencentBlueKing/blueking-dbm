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

// Package logger provides the process-wide logging facade for dbha-v2.
package logger

import (
	"log"
	"os"
	"sync/atomic"

	dbmlogger "dbm-services/common/go-pubpkg/logger"

	"go.uber.org/zap"
)

// Logger is a universal logging interface that can be
// flexibly replaced with other logging libraries
// without interfering with the operational logic
// of business code.
type Logger interface {
	OriginLogger() *zap.Logger

	Debug(format string, args ...any)
	Info(format string, args ...any)
	Warn(format string, args ...any)
	Error(format string, args ...any)
	Fatal(format string, args ...any)
}

// Level is the minimum enabled log severity.
type Level string

// String returns the canonical level name.
func (l Level) String() string {
	return string(l)
}

const (
	// DebugLevel enables debug and above.
	DebugLevel Level = "debug"
	// InfoLevel enables info and above.
	InfoLevel Level = "info"
	// WarnLevel enables warn and above.
	WarnLevel Level = "warn"
	// ErrorLevel enables error and above.
	ErrorLevel Level = "error"
	// FatalLevel enables fatal only.
	FatalLevel Level = "fatal"
)

// Config describes file rotation and the minimum level for constructed loggers.
type Config struct {
	FileName   string // destination log file path
	LogLevel   Level  // minimum enabled severity
	MaxSizeMB  int    // rotate after this size in megabytes
	MaxBackups int    // max retained rotated files
	MaxAge     int    // max days to keep a rotated file
}

type loggerHolder struct {
	l Logger
}

var dblog atomic.Value

func currentLogger() Logger {
	v := dblog.Load()
	if v == nil {
		return nil
	}
	h, ok := v.(*loggerHolder)
	if !ok || h == nil {
		return nil
	}
	return h.l
}

func fallbackPrint(format string, args ...any) {
	log.Printf(format, args...)
}

func fallbackFatal(format string, args ...any) {
	log.Fatalf(format, args...)
}

// SetLogger installs the process-wide logger. Passing nil restores stdlib fallback.
func SetLogger(log Logger) {
	dblog.Store(&loggerHolder{l: log})
}

// Log returns the process-wide logger, or nil when unset.
func Log() Logger {
	return currentLogger()
}

// Debug writes a debug message through the process-wide logger.
func Debug(format string, args ...any) {
	if l := currentLogger(); l != nil {
		l.Debug(format, args...)
		return
	}
	fallbackPrint(format, args...)
}

// Debugf is equivalent to Debug; kept for existing call sites.
func Debugf(format string, args ...any) {
	Debug(format, args...)
}

// Info writes an info message through the process-wide logger.
func Info(format string, args ...any) {
	if l := currentLogger(); l != nil {
		l.Info(format, args...)
		return
	}
	fallbackPrint(format, args...)
}

// Infof is equivalent to Info; kept for existing call sites.
func Infof(format string, args ...any) {
	Info(format, args...)
}

// Warn writes a warning through the process-wide logger.
func Warn(format string, args ...any) {
	if l := currentLogger(); l != nil {
		l.Warn(format, args...)
		return
	}
	fallbackPrint(format, args...)
}

// Warnf is equivalent to Warn; kept for existing call sites.
func Warnf(format string, args ...any) {
	Warn(format, args...)
}

// Error writes an error message through the process-wide logger.
func Error(format string, args ...any) {
	if l := currentLogger(); l != nil {
		l.Error(format, args...)
		return
	}
	fallbackPrint(format, args...)
}

// Errorf is equivalent to Error; kept for existing call sites.
func Errorf(format string, args ...any) {
	Error(format, args...)
}

// Fatal writes a fatal message through the process-wide logger, then exits.
func Fatal(format string, args ...any) {
	if l := currentLogger(); l != nil {
		l.Fatal(format, args...)
		return
	}
	fallbackFatal(format, args...)
}

// Fatalf is equivalent to Fatal; kept for existing call sites.
func Fatalf(format string, args ...any) {
	Fatal(format, args...)
}

func init() {
	// NOTE: go-pubpkg/trace prints at info during its package init.
	// Install an ErrorLevel dbm logger first so that noise is suppressed.
	hackerLogger := dbmlogger.New(os.Stderr, false, dbmlogger.ErrorLevel)
	dbmlogger.ResetDefault(hackerLogger)
	dbmlogger.Sync()
}
