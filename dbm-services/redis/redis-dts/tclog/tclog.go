// Package tclog ..
package tclog

import (
	"time"

	"github.com/spf13/viper"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Logger is a global log descripter
var Logger *zap.Logger

// timeEncoder format log time
func timeEncoder(t time.Time, enc zapcore.PrimitiveArrayEncoder) {
	enc.AppendString(t.Format("2006-01-02 15:04:05.000 -07:00"))
}

// InitStdoutLog 所有日志都将被输出到标准输出中
func InitStdoutLog() {
	debug := viper.GetBool("TENDIS_DEBUG")
	var level zap.AtomicLevel
	if debug == true {
		level = zap.NewAtomicLevelAt(zapcore.DebugLevel)
	} else {
		level = zap.NewAtomicLevelAt(zapcore.InfoLevel)
	}
	cfg := zap.Config{
		Encoding:         "json",
		Level:            level,
		OutputPaths:      []string{"stdout"},
		ErrorOutputPaths: []string{"stdout"},
		EncoderConfig: zapcore.EncoderConfig{
			MessageKey: "message",

			LevelKey: "level",

			TimeKey:    "time",
			EncodeTime: zapcore.ISO8601TimeEncoder,

			CallerKey:    "caller",
			EncodeCaller: zapcore.ShortCallerEncoder,

			NameKey:       "logger",
			StacktraceKey: "stacktrace",

			LineEnding:     zapcore.DefaultLineEnding,
			EncodeLevel:    zapcore.LowercaseLevelEncoder,
			EncodeDuration: zapcore.SecondsDurationEncoder,
		},
	}
	Logger, _ = cfg.Build()
}
func newEncoderConfig() zapcore.EncoderConfig {
	return zapcore.EncoderConfig{
		// Keys can be anything except the empty string.
		TimeKey:        "timestamp",
		LevelKey:       "level",
		NameKey:        "name",
		CallerKey:      "file",
		MessageKey:     "msg",
		StacktraceKey:  "stacktrace",
		LineEnding:     zapcore.DefaultLineEnding,
		EncodeLevel:    zapcore.CapitalLevelEncoder,
		EncodeTime:     timeEncoder,
		EncodeDuration: zapcore.StringDurationEncoder,
		EncodeCaller:   zapcore.ShortCallerEncoder,
	}
}

// InitMainlog 所有日志输出到log/main.log文件中
func InitMainlog() {
	debug := viper.GetBool("TENDIS_DEBUG")
	var level zap.AtomicLevel
	if debug == true {
		level = zap.NewAtomicLevelAt(zapcore.DebugLevel)
	} else {
		level = zap.NewAtomicLevelAt(zapcore.InfoLevel)
	}
	w := zapcore.AddSync(&lumberjack.Logger{
		Filename:   "log/main.log",
		MaxSize:    500, // megabytes
		MaxBackups: 3,
		MaxAge:     28, // days
	})
	core := zapcore.NewTee(
		// 同时输出到文件 和 stdout
		zapcore.NewCore(zapcore.NewJSONEncoder(newEncoderConfig()), zapcore.AddSync(w), level),
		// zapcore.NewCore(zapcore.NewJSONEncoder(newEncoderConfig()), zapcore.AddSync(os.Stdout), level),
	)
	Logger = zap.New(core, zap.AddCaller())
}

// NewFileLogger 新建一个logger
func NewFileLogger(logFile string) *zap.Logger {
	debug := viper.GetBool("TENDIS_DEBUG")
	var level zap.AtomicLevel
	if debug == true {
		level = zap.NewAtomicLevelAt(zapcore.DebugLevel)
	} else {
		level = zap.NewAtomicLevelAt(zapcore.InfoLevel)
	}
	w := zapcore.AddSync(&lumberjack.Logger{
		Filename:   logFile,
		MaxSize:    500, // megabytes
		MaxBackups: 3,
		MaxAge:     28, // days
	})
	core := zapcore.NewTee(
		// 同时输出到文件 和 stdout
		zapcore.NewCore(zapcore.NewJSONEncoder(newEncoderConfig()), zapcore.AddSync(w), level),
		// zapcore.NewCore(zapcore.NewJSONEncoder(newEncoderConfig()), zapcore.AddSync(os.Stdout), level),
	)
	return zap.New(core, zap.AddCaller())
}
