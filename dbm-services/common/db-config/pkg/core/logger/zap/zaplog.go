package zap

import (
	"bk-dbconfig/pkg/core/logger/base"
	"fmt"

	"go.uber.org/zap"
)

type zapLogger struct{}

// NewLogger TODO
func NewLogger() *zapLogger {
	return &zapLogger{}
}

// ImpleLogger TODO
func (s *zapLogger) ImpleLogger() {}

// Init TODO
func (s *zapLogger) Init() {}

// Debug TODO
func (s *zapLogger) Debug(format string, args ...interface{}) {
	GetLogger().Debug(fmt.Sprintf(format, args...))
}

// Info TODO
func (s *zapLogger) Info(format string, args ...interface{}) {
	GetLogger().Info(fmt.Sprintf(format, args...))
}

// Warn TODO
func (s *zapLogger) Warn(format string, args ...interface{}) {
	GetLogger().Warn(fmt.Sprintf(format, args...))
}

// Error 用于错误处理
func (s *zapLogger) Error(format string, args ...interface{}) {
	GetLogger().Error(fmt.Sprintf(format, args...))
}

// Fatal 注意: 此方法将导致程序终止!!!
func (s *zapLogger) Fatal(format string, args ...interface{}) {
	GetLogger().Fatal(fmt.Sprintf(format, args...))
}

// Panic 注意: 此方法将导致panic!!!
func (s *zapLogger) Panic(format string, args ...interface{}) {
	GetLogger().Panic(fmt.Sprintf(format, args...))
}

// WithFields 指定fields
func (s *zapLogger) WithFields(mapFields map[string]interface{}) base.ILogger {
	fields := make([]zap.Field, 0, len(mapFields))
	for key, val := range mapFields {
		fields = append(fields, zap.Any(key, val))
	}

	return &zapFields{fields}
}

// GetLogger TODO
func GetLogger() *zap.Logger {
	return zap.L()
}
