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
	"context"
	"errors"
	"os"
	"testing"
	"time"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	gormlogger "gorm.io/gorm/logger"
)

// mockLogger implements Logger interface for testing
type mockLogger struct {
	debugCalled bool
	infoCalled  bool
	warnCalled  bool
	errorCalled bool
	fatalCalled bool
	lastFormat  string
	lastArgs    []any
}

func newMockLogger() *mockLogger {
	return &mockLogger{}
}

func (m *mockLogger) OriginLogger() *zap.Logger {
	return zap.NewNop()
}

func (m *mockLogger) Debug(format string, args ...any) {
	m.debugCalled = true
	m.lastFormat = format
	m.lastArgs = args
}

func (m *mockLogger) Info(format string, args ...any) {
	m.infoCalled = true
	m.lastFormat = format
	m.lastArgs = args
}

func (m *mockLogger) Warn(format string, args ...any) {
	m.warnCalled = true
	m.lastFormat = format
	m.lastArgs = args
}

func (m *mockLogger) Error(format string, args ...any) {
	m.errorCalled = true
	m.lastFormat = format
	m.lastArgs = args
}

func (m *mockLogger) Fatal(format string, args ...any) {
	m.fatalCalled = true
	m.lastFormat = format
	m.lastArgs = args
}

// Verify mockLogger implements Logger interface
var _ Logger = (*mockLogger)(nil)

// ==================== logger.go tests ====================

func TestLevel_String(t *testing.T) {
	tests := []struct {
		level Level
		want  string
	}{
		{DebugLevel, "debug"},
		{InfoLevel, "info"},
		{WarnLevel, "warn"},
		{ErrorLevel, "error"},
		{FatalLevel, "fatal"},
	}

	for _, tt := range tests {
		t.Run(tt.want, func(t *testing.T) {
			if got := tt.level.String(); got != tt.want {
				t.Fatalf("Level.String() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestSetLoggerAndLog(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	if Log() != mock {
		t.Fatal("Log() should return the set logger")
	}
}

func TestDebug(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	Debug("test %s", "debug")
	if !mock.debugCalled {
		t.Fatal("Debug() should call logger.Debug()")
	}
	if mock.lastFormat != "test %s" {
		t.Fatalf("lastFormat = %v, want test %%s", mock.lastFormat)
	}
}

func TestDebugf(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	Debugf("test %s", "debugf")
	if !mock.debugCalled {
		t.Fatal("Debugf() should call logger.Debug()")
	}
}

func TestInfo(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	Info("test %s", "info")
	if !mock.infoCalled {
		t.Fatal("Info() should call logger.Info()")
	}
}

func TestInfof(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	Infof("test %s", "infof")
	if !mock.infoCalled {
		t.Fatal("Infof() should call logger.Info()")
	}
}

func TestWarn(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	Warn("test %s", "warn")
	if !mock.warnCalled {
		t.Fatal("Warn() should call logger.Warn()")
	}
}

func TestWarnf(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	Warnf("test %s", "warnf")
	if !mock.warnCalled {
		t.Fatal("Warnf() should call logger.Warn()")
	}
}

func TestError(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	Error("test %s", "error")
	if !mock.errorCalled {
		t.Fatal("Error() should call logger.Error()")
	}
}

func TestErrorf(t *testing.T) {
	mock := newMockLogger()
	SetLogger(mock)

	Errorf("test %s", "errorf")
	if !mock.errorCalled {
		t.Fatal("Errorf() should call logger.Error()")
	}
}

func TestLogWithNilLogger(t *testing.T) {
	SetLogger(nil)

	// These should not panic when dblog is nil
	Debug("test nil debug")
	Info("test nil info")
	Warn("test nil warn")
	Error("test nil error")
}

// ==================== zap_logger.go tests ====================

func TestConvertLevel(t *testing.T) {
	tests := []struct {
		level Level
		want  zapcore.Level
	}{
		{DebugLevel, zapcore.DebugLevel},
		{InfoLevel, zapcore.InfoLevel},
		{ErrorLevel, zapcore.ErrorLevel},
		{FatalLevel, zapcore.FatalLevel},
		{Level("unknown"), zapcore.InfoLevel},
	}

	for _, tt := range tests {
		t.Run(tt.level.String(), func(t *testing.T) {
			if got := convertLevel(tt.level); got != tt.want {
				t.Fatalf("convertLevel(%v) = %v, want %v", tt.level, got, tt.want)
			}
		})
	}
}

func TestNewZapLogger(t *testing.T) {
	tmpFile := "/tmp/test_zap_logger.log"
	defer os.Remove(tmpFile)

	config := Config{
		FileName:   tmpFile,
		LogLevel:   DebugLevel,
		MaxSizeMB:  10,
		MaxBackups: 3,
		MaxAge:     7,
	}

	logger := NewZapLogger(config)
	if logger == nil {
		t.Fatal("NewZapLogger() returned nil")
	}

	zapLogger, ok := logger.(*ZapLogger)
	if !ok {
		t.Fatal("NewZapLogger() should return *ZapLogger")
	}

	if zapLogger.OriginLogger() == nil {
		t.Fatal("OriginLogger() should not return nil")
	}
}

func TestZapLogger_Methods(t *testing.T) {
	tmpFile := "/tmp/test_zap_methods.log"
	defer os.Remove(tmpFile)

	config := Config{
		FileName:   tmpFile,
		LogLevel:   DebugLevel,
		MaxSizeMB:  10,
		MaxBackups: 3,
		MaxAge:     7,
	}

	logger := NewZapLogger(config).(*ZapLogger)

	// These should not panic
	logger.Debug("debug message %s", "test")
	logger.Info("info message %s", "test")
	logger.Warn("warn message %s", "test")
	logger.Error("error message %s", "test")

	err := logger.Sync()
	if err != nil {
		t.Logf("Sync() returned error (may be expected): %v", err)
	}
}

// ==================== gorm_logger.go tests ====================

func TestNewGormLogger(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{
		SlowThreshold:             200 * time.Millisecond,
		IgnoreRecordNotFoundError: true,
	}

	gormLog := NewGormLogger(mock, cfg)
	if gormLog == nil {
		t.Fatal("NewGormLogger() returned nil")
	}
	if gormLog.logger != mock {
		t.Fatal("GormLogger.logger should be the provided logger")
	}
	if gormLog.cfg != cfg {
		t.Fatal("GormLogger.cfg should be the provided config")
	}
}

func TestGormLogger_LogMode(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{}
	gormLog := NewGormLogger(mock, cfg)

	newLog := gormLog.LogMode(gormlogger.Info)
	if newLog == nil {
		t.Fatal("LogMode() returned nil")
	}
	if newLog == gormLog {
		t.Fatal("LogMode() should return a new logger instance")
	}
}

func TestGormLogger_Info(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{}
	gormLog := NewGormLogger(mock, cfg)

	gormLog.Info(context.Background(), "test info %s", "message")
	if !mock.infoCalled {
		t.Fatal("Info() should call underlying logger.Info()")
	}
}

func TestGormLogger_Warn(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{}
	gormLog := NewGormLogger(mock, cfg)

	gormLog.Warn(context.Background(), "test warn %s", "message")
	if !mock.warnCalled {
		t.Fatal("Warn() should call underlying logger.Warn()")
	}
}

func TestGormLogger_Error(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{}
	gormLog := NewGormLogger(mock, cfg)

	gormLog.Error(context.Background(), "test error %s", "message")
	if !mock.errorCalled {
		t.Fatal("Error() should call underlying logger.Error()")
	}
}

func TestGormLogger_NilLogger(t *testing.T) {
	cfg := &gormlogger.Config{}
	gormLog := NewGormLogger(nil, cfg)

	// These should not panic with nil logger
	gormLog.Info(context.Background(), "test")
	gormLog.Warn(context.Background(), "test")
	gormLog.Error(context.Background(), "test")
}

func TestGormLogger_Trace_Success(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{
		SlowThreshold: 200 * time.Millisecond,
	}
	gormLog := NewGormLogger(mock, cfg)

	begin := time.Now()
	fc := func() (string, int64) {
		return "SELECT * FROM users", 10
	}

	gormLog.Trace(context.Background(), begin, fc, nil)
	if !mock.debugCalled {
		t.Fatal("Trace() should call Debug() for successful queries")
	}
}

func TestGormLogger_Trace_WithError(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{
		SlowThreshold:             200 * time.Millisecond,
		IgnoreRecordNotFoundError: false,
	}
	gormLog := NewGormLogger(mock, cfg)

	begin := time.Now()
	fc := func() (string, int64) {
		return "SELECT * FROM users WHERE id = 1", 0
	}

	gormLog.Trace(context.Background(), begin, fc, errors.New("some error"))
	if !mock.errorCalled {
		t.Fatal("Trace() should call Error() when error occurs")
	}
}

func TestGormLogger_Trace_SlowQuery(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{
		SlowThreshold: 1 * time.Nanosecond,
	}
	gormLog := NewGormLogger(mock, cfg)

	begin := time.Now().Add(-1 * time.Second)
	fc := func() (string, int64) {
		return "SELECT * FROM large_table", 1000
	}

	gormLog.Trace(context.Background(), begin, fc, nil)
	if !mock.errorCalled {
		t.Fatal("Trace() should call Error() for slow queries")
	}
}

func TestGormLogger_Trace_NoRows(t *testing.T) {
	mock := newMockLogger()
	cfg := &gormlogger.Config{
		SlowThreshold: 200 * time.Millisecond,
	}
	gormLog := NewGormLogger(mock, cfg)

	begin := time.Now()
	fc := func() (string, int64) {
		return "DELETE FROM users", -1
	}

	gormLog.Trace(context.Background(), begin, fc, nil)
	if !mock.debugCalled {
		t.Fatal("Trace() should call Debug() for queries with -1 rows")
	}
}

// ==================== Config tests ====================

func TestConfig(t *testing.T) {
	cfg := Config{
		FileName:   "/var/log/test.log",
		LogLevel:   InfoLevel,
		MaxSizeMB:  100,
		MaxBackups: 5,
		MaxAge:     30,
	}

	if cfg.FileName != "/var/log/test.log" {
		t.Fatalf("FileName = %v, want /var/log/test.log", cfg.FileName)
	}
	if cfg.LogLevel != InfoLevel {
		t.Fatalf("LogLevel = %v, want info", cfg.LogLevel)
	}
	if cfg.MaxSizeMB != 100 {
		t.Fatalf("MaxSizeMB = %v, want 100", cfg.MaxSizeMB)
	}
	if cfg.MaxBackups != 5 {
		t.Fatalf("MaxBackups = %v, want 5", cfg.MaxBackups)
	}
	if cfg.MaxAge != 30 {
		t.Fatalf("MaxAge = %v, want 30", cfg.MaxAge)
	}
}
