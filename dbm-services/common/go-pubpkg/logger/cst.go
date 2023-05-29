package logger

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// Level TODO
type Level = zapcore.Level

const (
	// InfoLevel TODO
	InfoLevel = zap.InfoLevel
	// WarnLevel TODO
	WarnLevel = zap.WarnLevel
	// ErrorLevel TODO
	ErrorLevel = zap.ErrorLevel
	// DPanicLevel TODO
	DPanicLevel = zap.DPanicLevel
	// PanicLevel TODO
	PanicLevel = zap.PanicLevel
	// FatalLevel TODO
	FatalLevel = zap.FatalLevel
	// DebugLevel TODO
	DebugLevel = zap.DebugLevel
)

// DatetimeUnion TODO
const DatetimeUnion = "20160102150405"
