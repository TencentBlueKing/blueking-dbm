package logrus

import (
	"bk-dbconfig/pkg/core/logger/base"
	"fmt"

	"github.com/sirupsen/logrus"
)

// 处理带fields的日志
type logrusFields struct {
	fields logrus.Fields
}

// ImpleLogger TODO
func (s *logrusFields) ImpleLogger() {}

// Init TODO
func (s *logrusFields) Init() {}

// Debug TODO
func (s *logrusFields) Debug(format string, args ...interface{}) {
	GetLogger().WithFields(s.fields).Debugf(format, args...)
}

// Info TODO
func (s *logrusFields) Info(format string, args ...interface{}) {
	GetLogger().WithFields(s.fields).Infof(format, args...)
}

// Warn TODO
func (s *logrusFields) Warn(format string, args ...interface{}) {
	GetLogger().WithFields(s.fields).Warnf(format, args...)
}

// Error 用于错误处理
func (s *logrusFields) Error(format string, args ...interface{}) {
	GetLogger().WithFields(s.fields).Errorf(format, args...)
}

// Fatal TODO
func (s *logrusFields) Fatal(format string, args ...interface{}) {
	GetLogger().WithFields(s.fields).Fatalf(format, args...)
}

// Panic TODO
func (s *logrusFields) Panic(format string, args ...interface{}) {
	GetLogger().WithFields(s.fields).Panicf(format, args...)
}

// String 用于打印
func (s *logrusFields) String(format string, args ...interface{}) string {
	return fmt.Sprintf(format, args...)
}

// WithFields 支持链式调用
func (s *logrusFields) WithFields(mapFields map[string]interface{}) base.ILogger {
	s.fields = mapFields

	return s
}
