package logger

import (
	"fmt"

	"go.uber.org/zap"
)

// Field TODO
type Field = zap.Field

// Logger TODO
type Logger struct {
	Zap    *zap.Logger
	Level  Level
	Fields []zap.Field
}

// Debug TODO
func (l *Logger) Debug(format string, args ...interface{}) {
	l.Zap.Debug(fmt.Sprintf(format, args...), l.Fields...)
}

// Info TODO
func (l *Logger) Info(format string, args ...interface{}) {
	l.Zap.Info(fmt.Sprintf(format, args...), l.Fields...)
}

// Warn TODO
func (l *Logger) Warn(format string, args ...interface{}) {
	l.Zap.Warn(fmt.Sprintf(format, args...), l.Fields...)
}

// Error 用于错误处理
func (l *Logger) Error(format string, args ...interface{}) {
	l.Zap.Error(fmt.Sprintf(format, args...), l.Fields...)
}

// DPanic TODO
func (l *Logger) DPanic(format string, args ...interface{}) {
	l.Zap.DPanic(fmt.Sprintf(format, args...), l.Fields...)
}

// Panic TODO
func (l *Logger) Panic(format string, args ...interface{}) {
	l.Zap.Panic(fmt.Sprintf(format, args...), l.Fields...)
}

// Fatal TODO
func (l *Logger) Fatal(format string, args ...interface{}) {
	l.Zap.Fatal(fmt.Sprintf(format, args...), l.Fields...)
}

// With TODO
func (l *Logger) With(fields ...Field) *Logger {
	logger := l.Zap.With(fields...)
	l.Zap = logger
	return l
}

// Sync TODO
func (l *Logger) Sync() error {
	return l.Zap.Sync()
}

// GetLogger TODO
func GetLogger() *zap.Logger {
	return zap.L()
}
