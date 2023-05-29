package logger

import (
	"io"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// New TODO
//
//	@receiver writer
//	@receiver format 是否格式化日志
//	@receiver level
//	@receiver extMap
//	@return *Logger
func New(writer io.Writer, format bool, level Level, extMap ...map[string]string) *Logger {
	if writer == nil {
		panic("the writer is nil")
	}

	cfg := zap.NewProductionConfig()
	cfg.EncoderConfig = zapcore.EncoderConfig{
		MessageKey:     "msg",
		LevelKey:       "levelname",
		TimeKey:        "time",
		NameKey:        "name",
		FunctionKey:    "funcName",
		StacktraceKey:  "stacktrace",
		CallerKey:      "caller",
		SkipLineEnding: false,
		LineEnding:     zapcore.DefaultLineEnding,
		EncodeLevel:    zapcore.LowercaseLevelEncoder,
		EncodeTime:     zapcore.RFC3339TimeEncoder,
		EncodeDuration: zapcore.SecondsDurationEncoder,
		EncodeName:     zapcore.FullNameEncoder,
		EncodeCaller:   zapcore.ShortCallerEncoder,
	}

	encoder := NewConsoleEncoder(cfg.EncoderConfig)
	if format {
		encoder = NewEncoder(cfg.EncoderConfig)
	}
	core := zapcore.NewCore(
		encoder,
		zapcore.AddSync(writer),
		level,
	)
	logger := &Logger{
		Zap:   zap.New(core),
		Level: level,
	}

	// 初始化默认字段
	fs := make([]zap.Field, 0)
	for _, ext := range extMap {
		for key, value := range ext {
			fs = append(fs, zap.String(key, value))
		}
	}
	logger = logger.With(fs...)
	return logger
}
