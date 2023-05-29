package zap

// zap是日志功能的一种实现。
// 支持特性：
// 1. 支持2种日志格式: json 和 logfmt
// 2. 支持日志轮换: 可按文件大小，时间轮换，可设置保留备份文件数。

import (
	"bk-dbconfig/pkg/core/config"
	"bk-dbconfig/pkg/core/logger/lumberjack"
	"bk-dbconfig/pkg/core/safego"
	stdlog "log"
	"net/http"
	"os"
	"time"

	zapfmt "github.com/jsternberg/zap-logfmt"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var (
	_LOGHOSTNAME = ""
)

// TODO log by date

// New 初始化，并返回日志对象。
func New() *zapLogger {
	// 初始化全局变量
	_LOGHOSTNAME, _ = os.Hostname()

	// 设置时间戳格式
	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.EncodeTime = func(ts time.Time, encoder zapcore.PrimitiveArrayEncoder) {
		ts = ts.Local()
		if !config.Logger.LocalTime {
			ts = ts.UTC()
		}
		encoder.AppendString(ts.Format(config.Logger.TimeFormat))
	}

	// 设置日志格式为
	var encoder zapcore.Encoder
	switch config.Logger.Formater {
	case "json":
		encoder = zapcore.NewJSONEncoder(encoderConfig)
	case "console":
		encoder = zapcore.NewConsoleEncoder(encoderConfig)
	default:
		encoder = zapfmt.NewEncoder(encoderConfig)
	}

	// 设置日志rotate
	var writerSyncer zapcore.WriteSyncer
	switch config.Logger.Output {
	case "", "stdout":
		writerSyncer = zapcore.AddSync(os.Stdout)
	case "stderr":
		writerSyncer = zapcore.AddSync(os.Stderr)
	default:
		if config.Logger.MaxSize == 0 && config.Logger.MaxBackups == 0 && config.Logger.MaxAge == 0 {
			// 未启动日志切换
			ws, _, err := zap.Open(config.Logger.Output)
			if err != nil {
				stdlog.Fatalf("Failed open log file: %s", config.Logger.Output)
				return nil
			}
			writerSyncer = ws
		} else {
			// 启用日志切换
			output := &lumberjack.Logger{
				Filename:   config.Logger.Output,
				MaxSize:    config.Logger.MaxSize,
				MaxBackups: config.Logger.MaxBackups,
				MaxAge:     config.Logger.MaxAge,
				LocalTime:  config.Logger.LocalTime,
			}
			writerSyncer = zapcore.AddSync(output)
		}
	}

	// info level
	atomicLevel := zap.NewAtomicLevel()

	// 使用 zapcore
	core := zapcore.NewCore(
		encoder,
		writerSyncer,
		atomicLevel,
	)

	// 生成logger
	logger := zap.New(core)

	// 显 caller
	// logger = logger.WithOptions(zap.AddCaller())

	// 显示stacktrace
	// logger = logger.WithOptions(zap.AddStacktrace(zap.ErrorLevel))

	// 初始化fields
	fs := make([]zap.Field, 0)
	fs = append(fs, zap.String("hostname", _LOGHOSTNAME))
	logger = logger.WithOptions(zap.Fields(fs...))

	// 设置level
	switch config.Logger.Level {
	case "debug":
		atomicLevel.SetLevel(zap.DebugLevel)
	case "info":
		atomicLevel.SetLevel(zap.InfoLevel)
	case "warning", "warn":
		atomicLevel.SetLevel(zap.WarnLevel)
	case "error":
		atomicLevel.SetLevel(zap.ErrorLevel)
	case "fatal":
		atomicLevel.SetLevel(zap.FatalLevel)
	case "panic":
		atomicLevel.SetLevel(zap.PanicLevel)
	default:
		atomicLevel.SetLevel(zap.InfoLevel)
	}

	zap.ReplaceGlobals(logger)

	// 动态调整level服务
	if config.Logger.LevelServer {
		mux := http.NewServeMux()
		mux.Handle("/log_level", atomicLevel)
		safego.Go(func() {
			_ = http.ListenAndServe("localhost:10900", mux)
		})
	}

	return NewLogger()
}
