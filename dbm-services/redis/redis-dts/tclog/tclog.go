// Package tclog ..
package tclog

import (
	"fmt"
	"strings"
	"time"

	"github.com/robfig/cron/v3"
	"github.com/spf13/viper"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Logger is a global log descripter
var Logger *zap.Logger

// GlobCronLogger 适配robfig/cron logger
var GlobCronLogger *cronLogAdapter

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

	GlobCronLogger = &cronLogAdapter{}
	GlobCronLogger.Logger = Logger
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

// 无实际作用,仅确保实现了 cron.Logger  接口
var _ cron.Logger = (*cronLogAdapter)(nil)

// cronLogAdapter 适配器,目标兼容 go.uber.org/zap.Logger 和 robfig/cron.Logger的接口
type cronLogAdapter struct {
	*zap.Logger
}

// Error error
func (l *cronLogAdapter) Error(err error, msg string, keysAndValues ...interface{}) {
	keysAndValues = formatTimes(keysAndValues)
	l.Error(err, fmt.Sprintf(formatString(len(keysAndValues)+2), append([]interface{}{msg, "error", err},
		keysAndValues...)...))
}

// Info info
func (l *cronLogAdapter) Info(msg string, keysAndValues ...interface{}) {
	keysAndValues = formatTimes(keysAndValues)
	l.Logger.Info(fmt.Sprintf(formatString(len(keysAndValues)), append([]interface{}{msg}, keysAndValues...)...))
}

// formatString returns a logfmt-like format string for the number of
// key/values.
func formatString(numKeysAndValues int) string {
	var sb strings.Builder
	sb.WriteString("%s")
	if numKeysAndValues > 0 {
		sb.WriteString(", ")
	}
	for i := 0; i < numKeysAndValues/2; i++ {
		if i > 0 {
			sb.WriteString(", ")
		}
		sb.WriteString("%v=%v")
	}
	return sb.String()
}

// formatTimes formats any time.Time values as RFC3339.
func formatTimes(keysAndValues []interface{}) []interface{} {
	var formattedArgs []interface{}
	for _, arg := range keysAndValues {
		if t, ok := arg.(time.Time); ok {
			arg = t.Format(time.RFC3339)
		}
		formattedArgs = append(formattedArgs, arg)
	}
	return formattedArgs
}
