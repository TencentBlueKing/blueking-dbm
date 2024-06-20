package logger

import (
	"bk-dnsapi/pkg/logger/base"
	"bk-dnsapi/pkg/logger/zap"
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

// Info Info
func Info(format string, args ...interface{}) {
	DefaultLogger.Info(format, args...)
}

// Warn Warn
func Warn(format string, args ...interface{}) {
	DefaultLogger.Warn(format, args...)
}

// Error Error
func Error(format string, args ...interface{}) {
	DefaultLogger.Error(format, args...)
}

// Fatal Fatal
func Fatal(format string, args ...interface{}) {
	DefaultLogger.Fatal(format, args...)
}

// Panic Panic
func Panic(format string, args ...interface{}) {
	DefaultLogger.Panic(format, args...)
}

// WithFields WithFields
func WithFields(mapFields map[string]interface{}) base.ILogger {
	return DefaultLogger.WithFields(mapFields)
}
