package mylogger

import (
	"bk-dbconfig/pkg/core/logger/lumberjack"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path"
	"path/filepath"
	"strings"
)

var mongoLogger *slog.Logger

func GetMongoLogger() *slog.Logger {
	return mongoLogger
}

// InitMongoLoggerOnce 初始化mongo logger
func InitMongoLoggerOnce() {
	if mongoLogger != nil {
		return
	}
	mongoLogger = createLogger(config.LogConfig.LogFileDir,
		config.LogConfig.Console, config.LogConfig.Json, config.LogConfig.Debug, "mongo")
}

// createLogger 创建logger. 可以指定日志文件后缀. 比如 mongo, mysql, redis, etc.
func createLogger(logFileDir string, console bool, json bool, debug bool, dbType string) *slog.Logger {
	executable, err := os.Executable()
	if err != nil {
		panic(err)
	}
	var ioWriters []io.Writer

	if console {
		ioWriters = append(ioWriters, os.Stdout)
	}

	if logFileDir != "" {
		if !path.IsAbs(logFileDir) {
			logFileDir = filepath.Join(filepath.Dir(executable), logFileDir)
		}
		err := os.MkdirAll(logFileDir, 0755)
		if err != nil {
			panic(err)
		}
		logFile := path.Join(logFileDir, fmt.Sprintf("%s-%s.log", filepath.Base(executable), dbType))
		// 优化：直接使用 OpenFile 创建文件（如果不存在），避免额外的 Stat 调用
		f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
		if err != nil {
			panic(err)
		}
		f.Close() // 立即关闭，lumberjack 会自己打开

		ioWriters = append(
			ioWriters, &lumberjack.Logger{
				Filename:   logFile,
				MaxAge:     5,
				MaxBackups: 5,
			},
		)
	}

	handleOpt := slog.HandlerOptions{
		AddSource:   true,
		ReplaceAttr: replaceSourceAttr,
	}

	if debug {
		handleOpt.Level = slog.LevelDebug
	} else {
		handleOpt.Level = slog.LevelInfo
	}

	var logger *slog.Logger
	if json {
		logger = slog.New(slog.NewJSONHandler(io.MultiWriter(ioWriters...), &handleOpt))
	} else {
		logger = slog.New(slog.NewTextHandler(io.MultiWriter(ioWriters...), &handleOpt))
	}
	return logger
}

// replaceSourceAttr 替换源文件路径和函数名
func replaceSourceAttr(groups []string, a slog.Attr) slog.Attr {
	if a.Key == slog.SourceKey {
		if src, ok := a.Value.Any().(*slog.Source); ok {
			// 优化文件路径处理：使用 LastIndex 避免 Split+Join 的内存分配
			// -> "mongodb_rpc/mongodb_shell.go"
			if idx := strings.LastIndex(src.File, "/"); idx >= 0 {
				// 找到倒数第二个斜杠，保留最后两层目录
				if prevIdx := strings.LastIndex(src.File[:idx], "/"); prevIdx >= 0 {
					src.File = src.File[prevIdx+1:]
				}
			}

			// 优化函数名处理：直接使用切片避免重复查找
			// -> "mongodb_rpc.(*MongoShell).Run.func1"
			if lastSlash := strings.LastIndex(src.Function, "/"); lastSlash >= 0 {
				src.Function = src.Function[lastSlash+1:]
			}
			a.Value = slog.AnyValue(src)
		}
	}
	return a
}
