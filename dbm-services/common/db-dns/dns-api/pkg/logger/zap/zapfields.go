package zap

import (
	"bk-dnsapi/pkg/logger/base"
	"fmt"

	"go.uber.org/zap"
)

// 处理带fields的日志
type zapFields struct {
	fields []zap.Field
}

// ImpleLogger ImpleLogger
func (s *zapFields) ImpleLogger() {}

// Init TODO
func (s *zapFields) Init() {}

// Debug Debug
func (s *zapFields) Debug(format string, args ...interface{}) {
	GetLogger().Debug(fmt.Sprintf(format, args...), s.fields...)
}

// Info Info
func (s *zapFields) Info(format string, args ...interface{}) {
	GetLogger().Info(fmt.Sprintf(format, args...), s.fields...)
}

// Warn Warn
func (s *zapFields) Warn(format string, args ...interface{}) {
	GetLogger().Warn(fmt.Sprintf(format, args...), s.fields...)
}

// Error 用于错误处理
func (s *zapFields) Error(format string, args ...interface{}) {
	GetLogger().Error(fmt.Sprintf(format, args...), s.fields...)
}

// Fatal Fatal
func (s *zapFields) Fatal(format string, args ...interface{}) {
	GetLogger().Fatal(fmt.Sprintf(format, args...), s.fields...)
}

// Panic Panic
func (s *zapFields) Panic(format string, args ...interface{}) {
	GetLogger().Panic(fmt.Sprintf(format, args...), s.fields...)
}

// WithFields 支持链式调用
func (s *zapFields) WithFields(mapFields map[string]interface{}) base.ILogger {
	if s.fields == nil {
		s.fields = make([]zap.Field, 0, len(mapFields))
	}

	for key, val := range mapFields {
		s.fields = append(s.fields, zap.Any(key, val))
	}

	return s
}

// String 用于打印
func (s *zapFields) String(format string, args ...interface{}) string {
	return fmt.Sprintf(format, args...)
}
