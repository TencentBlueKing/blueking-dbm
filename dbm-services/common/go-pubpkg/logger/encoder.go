package logger

import (
	"runtime"

	"go.uber.org/zap"
	"go.uber.org/zap/buffer"
	"go.uber.org/zap/zapcore"
)

// CallerEncoder TODO
type CallerEncoder struct {
	zapcore.Encoder
}

// NewEncoder TODO
func NewEncoder(cfg zapcore.EncoderConfig) zapcore.Encoder {
	return CallerEncoder{
		Encoder: zapcore.NewJSONEncoder(cfg),
	}
}

// NewConsoleEncoder TODO
func NewConsoleEncoder(cfg zapcore.EncoderConfig) zapcore.Encoder {
	return CallerEncoder{
		Encoder: zapcore.NewConsoleEncoder(cfg),
	}
}

// Clone TODO
func (enc CallerEncoder) Clone() zapcore.Encoder {
	return CallerEncoder{
		enc.Encoder.Clone(),
	}
}

// EncodeEntry TODO
func (enc CallerEncoder) EncodeEntry(entry zapcore.Entry, fields []zapcore.Field) (*buffer.Buffer, error) {
	pc, file, line, _ := runtime.Caller(5)
	filename := runtime.FuncForPC(pc).Name()
	fields = append(fields, zap.String("funcName", filename))
	fields = append(fields, zap.Int("lineno", line))
	fields = append(fields, zap.String("pathname", file))
	fields = append(fields, zap.String("tag", "actuator"))
	return enc.Encoder.EncodeEntry(entry, fields)
}
