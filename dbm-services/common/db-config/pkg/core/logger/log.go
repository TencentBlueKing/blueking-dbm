package logger

import (
	"bk-dbconfig/pkg/core/logger/base"
	"bk-dbconfig/pkg/core/logger/zap"
)

var (
	// DefaultLogger 确保不为空
	DefaultLogger base.ILogger = zap.New()
)

// InitLog 向后兼容的遗留函数。
func InitLog() {
	// DefaultLogger = zap.New()
}

// InitLogger 通用的初始化方法。
func InitLogger(logger base.ILogger) {
	DefaultLogger = logger
}

// Debug 以下为log模块的输出方法。
func Debug(format string, args ...interface{}) {
	DefaultLogger.Debug(format, args...)
}

// Info TODO
func Info(format string, args ...interface{}) {
	DefaultLogger.Info(format, args...)
}

// Warn TODO
func Warn(format string, args ...interface{}) {
	DefaultLogger.Warn(format, args...)
}

// Error TODO
func Error(format string, args ...interface{}) {
	DefaultLogger.Error(format, args...)
}

// Fatal TODO
func Fatal(format string, args ...interface{}) {
	DefaultLogger.Fatal(format, args...)
}

// Panic TODO
func Panic(format string, args ...interface{}) {
	DefaultLogger.Panic(format, args...)
}

// WithFields TODO
func WithFields(mapFields map[string]interface{}) base.ILogger {
	return DefaultLogger.WithFields(mapFields)
}

// Debugf 兼容
// Debug 以下为log模块的输出方法。
func Debugf(format string, args ...interface{}) {
	DefaultLogger.Debug(format, args...)
}

// Infof TODO
func Infof(format string, args ...interface{}) {
	DefaultLogger.Info(format, args...)
}

// Warnf TODO
func Warnf(format string, args ...interface{}) {
	DefaultLogger.Warn(format, args...)
}

// Errorf TODO
func Errorf(format string, args ...interface{}) {
	DefaultLogger.Error(format, args...)
}

// Fatalf TODO
func Fatalf(format string, args ...interface{}) {
	DefaultLogger.Fatal(format, args...)
}

// Panicf TODO
func Panicf(format string, args ...interface{}) {
	DefaultLogger.Panic(format, args...)
}
