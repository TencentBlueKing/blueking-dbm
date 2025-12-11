package utils

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/google/uuid"
	"gopkg.in/natefinch/lumberjack.v2"
)

func InitLogger(cfg *config.LogConfig) {
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

		logFile := filepath.Join(
			*cfg.LogFileDir,
			fmt.Sprintf("%s.%d.log", executableName, config.MonitorConfig.Port),
		)
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

		ioWriters = append(ioWriters, &lumberjack.Logger{
			Filename: logFile,
			MaxAge:   2,
			//MaxBackups: 2,
			Compress: false,
		})
	}

	handleOpt := slog.HandlerOptions{AddSource: cfg.Source}
	if cfg.Debug {
		handleOpt.Level = slog.LevelDebug
	} else {
		handleOpt.Level = slog.LevelInfo
	}

	if cfg.Json {
		config.Logger = slog.New(slog.NewJSONHandler(io.MultiWriter(ioWriters...), &handleOpt))
	} else {
		config.Logger = slog.New(slog.NewTextHandler(io.MultiWriter(ioWriters...), &handleOpt))
	}

	config.Logger = config.Logger.With("uuid", uuid.New().String())

	slog.SetDefault(config.Logger)
}
