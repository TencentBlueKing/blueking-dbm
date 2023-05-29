package logger

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// RotateOptions TODO
type RotateOptions struct {
	MaxSize    int
	MaxAge     int
	MaxBackups int
	Compress   bool
}

// TreeOption TODO
type TreeOption struct {
	FileName string
	Rpt      RotateOptions
	Lef      zap.LevelEnablerFunc
}

// NewRotate TODO
func NewRotate(ops []TreeOption, opts ...zap.Option) *Logger {
	var cores []zapcore.Core
	cfg := zap.NewProductionConfig()
	cfg.EncoderConfig = zapcore.EncoderConfig{
		MessageKey:     "msg",
		LevelKey:       "level",
		TimeKey:        "time",
		NameKey:        "name",
		CallerKey:      "caller",
		FunctionKey:    "func",
		StacktraceKey:  "stacktrace",
		SkipLineEnding: false,
		LineEnding:     zapcore.DefaultLineEnding,
		EncodeLevel:    zapcore.LowercaseLevelEncoder,
		EncodeTime:     zapcore.ISO8601TimeEncoder,
		EncodeDuration: zapcore.SecondsDurationEncoder,
		EncodeCaller:   zapcore.ShortCallerEncoder,
		EncodeName:     zapcore.FullNameEncoder,
	}
	for _, op := range ops {
		lv := zap.LevelEnablerFunc(func(level zapcore.Level) bool {
			return op.Lef(Level(level))
		})
		lj := zapcore.AddSync(&lumberjack.Logger{
			Filename:   op.FileName,
			MaxSize:    op.Rpt.MaxSize,
			MaxBackups: op.Rpt.MaxBackups,
			MaxAge:     op.Rpt.MaxAge,
			LocalTime:  true,
			Compress:   true,
		})

		core := zapcore.NewCore(zapcore.NewJSONEncoder(cfg.EncoderConfig), zapcore.AddSync(lj), lv)
		cores = append(cores, core)
	}
	logger := &Logger{
		Zap: zap.New(zapcore.NewTee(cores...), opts...),
	}

	return logger
}
