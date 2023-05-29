package logger

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

func TestCustomField(t *testing.T) {
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
				return level <= zap.InfoLevel
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
		field := &CustomField{
			UID:    fmt.Sprintf("%d", i),
			NodeID: fmt.Sprintf("node_id_%d", i),
			IP:     "127.0.0.1",
		}
		Warn("testing warn", zap.Inline(field))
	}

	assert.FileExists(t, "access.log")
	assert.FileExists(t, "error.log")
}

type CustomField struct {
	UID    string
	NodeID string
	IP     string
}

func (f CustomField) MarshalLogObject(enc zapcore.ObjectEncoder) error {
	enc.AddString("uid", f.UID)
	enc.AddString("node_id", f.NodeID)
	enc.AddString("ip", f.IP)
	return nil
}
