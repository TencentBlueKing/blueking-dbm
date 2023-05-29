package logrus

import (
	"bk-dbconfig/pkg/core/logger/base"

	"github.com/sirupsen/logrus"
)

type logrusLogger struct{}

// NewLogger TODO
func NewLogger() *logrusLogger {
	return &logrusLogger{}
}

// ImpleLogger TODO
func (s *logrusLogger) ImpleLogger() {}

// Init TODO
func (s *logrusLogger) Init() {}

// Debug TODO
func (s *logrusLogger) Debug(format string, args ...interface{}) {
	GetLogger().Debugf(format, args...)
}

// Info TODO
func (s *logrusLogger) Info(format string, args ...interface{}) {
	GetLogger().Infof(format, args...)
}

// Warn TODO
func (s *logrusLogger) Warn(format string, args ...interface{}) {
	GetLogger().Warnf(format, args...)
}

// Error 用于错误处理
func (s *logrusLogger) Error(format string, args ...interface{}) {
	GetLogger().Errorf(format, args...)
}

// Fatal 注意: 此方法将导致程序终止!!!
func (s *logrusLogger) Fatal(format string, args ...interface{}) {
	GetLogger().Fatalf(format, args...)
}

// Panic 注意: 此方法将导致panic!!!
func (s *logrusLogger) Panic(format string, args ...interface{}) {
	GetLogger().Panicf(format, args...)
}

// WithFields 指定fields
func (s *logrusLogger) WithFields(mapFields map[string]interface{}) base.ILogger {
	return &logrusFields{}
}

// GetLogger TODO
func GetLogger() *logrus.Entry {
	fields := logrus.Fields{
		"hostname": _LOGHOSTNAME,
	}

	return logrus.WithFields(fields)
}
