package logger

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

func TestRotate(t *testing.T) {
	var ops = []TreeOption{
		{
			FileName: "access.log",
			Rpt: RotateOptions{
				MaxSize:    1,
				MaxAge:     1,
				MaxBackups: 3,
				Compress:   true,
			},
			Lef: func(level zapcore.Level) bool {
				return level <= InfoLevel
			},
		},
		{
			FileName: "error.log",
			Rpt: RotateOptions{
				MaxSize:    1,
				MaxAge:     1,
				MaxBackups: 3,
				Compress:   true,
			},
			Lef: func(level zapcore.Level) bool {
				return level > zap.InfoLevel
			},
		},
	}

	logger := NewRotate(ops)
	ResetDefault(logger)
	for i := 0; i < 2000000; i++ {
		Info("testing ok", zap.String("tag", "test"), zap.Int("major version", 1))
		Error("testing crash", zap.String("tag", "test"), zap.Int("major version", 1))
	}

	assert.FileExists(t, "access.log")
	assert.FileExists(t, "error.log")
}
