package cmd

import (
	"fmt"
	"io"
	"os"
	"path/filepath"

	"dbm-services/riak/db-tools/riak-monitor/pkg/config"

	"github.com/natefinch/lumberjack"
	"golang.org/x/exp/slog"
)

var executable string
var executableName string
var executableDir string

func init() {
	executable, _ = os.Executable()
	// 获取可执行文件的名称
	executableName = filepath.Base(executable)
	// 获取可执行文件的路径
	executableDir = filepath.Dir(executable)
}

// initLogger 初始化日志格式
func initLogger(cfg *config.LogConfig) {
	var ioWriters []io.Writer

	// console打印日志
	if cfg.Console {
		ioWriters = append(ioWriters, os.Stdout)
	}

	// 日志文件记录日志
	if cfg.LogFileDir != nil {
		if !filepath.IsAbs(*cfg.LogFileDir) {
			*cfg.LogFileDir = filepath.Join(executableDir, *cfg.LogFileDir)
		}

		err := os.MkdirAll(*cfg.LogFileDir, 0755)
		if err != nil {
			panic(err)
		}

		logFile := filepath.Join(*cfg.LogFileDir, fmt.Sprintf("%s.log", executableName))
		_, err = os.Stat(logFile)
		if err != nil {
			// 目录不存在创建目录
			if os.IsNotExist(err) {
				_, err := os.Create(logFile)
				if err != nil {
					panic(err)
				}
			} else {
				panic(err)
			}
		}
		ioWriters = append(ioWriters, &lumberjack.Logger{Filename: logFile})
	}
	// 日志中添加源头信息，方便定位
	handleOpt := slog.HandlerOptions{AddSource: cfg.Source}
	if cfg.Debug {
		handleOpt.Level = slog.LevelDebug
	} else {
		handleOpt.Level = slog.LevelInfo
	}

	var logger *slog.Logger
	// 设置日志格式
	if cfg.Json {
		logger = slog.New(slog.NewJSONHandler(io.MultiWriter(ioWriters...), &handleOpt))
	} else {
		logger = slog.New(slog.NewTextHandler(io.MultiWriter(ioWriters...), &handleOpt))
	}

	slog.SetDefault(logger)
}
