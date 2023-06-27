package cmd

import (
	"fmt"
	"io"
	"os"
	"path/filepath"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"

	"golang.org/x/exp/slog"
	"gopkg.in/natefinch/lumberjack.v2"
)

var executable string
var executableName string
var executableDir string

func init() {
	executable, _ = os.Executable()
	executableName = filepath.Base(executable)
	executableDir = filepath.Dir(executable)
}

func initLogger(cfg *config.LogConfig) {
	var ioWriters []io.Writer

	if cfg.Console {
		ioWriters = append(ioWriters, os.Stdout)
	}

	if cfg.LogFileDir != nil {
		if !filepath.IsAbs(*cfg.LogFileDir) {
			*cfg.LogFileDir = filepath.Join(executableDir, *cfg.LogFileDir)
		}

		err := os.MkdirAll(*cfg.LogFileDir, 0755)
		if err != nil {
			panic(err)
		}

		// ToDo 修改目录宿主

		logFile := filepath.Join(*cfg.LogFileDir, fmt.Sprintf("%s.log", executableName))
		_, err = os.Stat(logFile)
		if err != nil {
			if os.IsNotExist(err) {
				_, err := os.Create(logFile)
				if err != nil {
					panic(err)
				}
				// ToDo 修改日志文件宿主
			} else {
				panic(err)
			}
		}

		ioWriters = append(ioWriters, &lumberjack.Logger{Filename: logFile})
	}

	handleOpt := slog.HandlerOptions{AddSource: cfg.Source}
	if cfg.Debug {
		handleOpt.Level = slog.LevelDebug
	} else {
		handleOpt.Level = slog.LevelInfo
	}

	var logger *slog.Logger
	if cfg.Json {
		logger = slog.New(slog.NewJSONHandler(
			io.MultiWriter(ioWriters...),
			&handleOpt),
		)

	} else {
		logger = slog.New(slog.NewTextHandler(
			io.MultiWriter(ioWriters...),
			&handleOpt),
		)
	}

	slog.SetDefault(logger)
}
