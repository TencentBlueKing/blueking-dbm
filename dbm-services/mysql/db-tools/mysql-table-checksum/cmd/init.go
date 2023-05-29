package cmd

import (
	"dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"

	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
	"gopkg.in/natefinch/lumberjack.v2"
)

var executable string
var executableName string
var executableDir string

func init() {
	// Here you will define your flags and configuration settings.
	// Cobra supports persistent flags, which, if defined here,
	// will be global for your application.

	// Cobra also supports local flags, which will only run
	// when this action is called directly.

	executable, _ = os.Executable()
	executableName = filepath.Base(executable)
	executableDir = filepath.Dir(executable)
}

func initLogger(cfg *config.LogConfig, mode config.CheckMode) {
	var ioWriters []io.Writer

	if cfg.Console {
		ioWriters = append(ioWriters, os.Stdout)
	}

	if cfg.LogFileDir != nil {
		if !path.IsAbs(*cfg.LogFileDir) {
			err := fmt.Errorf("log_file_dir need absolute dir")
			panic(err)
		}

		err := os.MkdirAll(*cfg.LogFileDir, 0755)
		if err != nil {
			panic(err)
		}

		// ToDo 修改目录宿主
		var logFile string
		if mode == config.GeneralMode {
			logFile = path.Join(
				*cfg.LogFileDir,
				fmt.Sprintf("%s_%d.log", executableName, config.ChecksumConfig.Port),
			)
		} else {
			logFile = path.Join(
				*cfg.LogFileDir,
				fmt.Sprintf(
					"%s_%d_%s.log",
					executableName,
					config.ChecksumConfig.Port,
					viper.GetString("uuid"),
				),
			)
		}

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
		logger = slog.New(handleOpt.NewJSONHandler(io.MultiWriter(ioWriters...)))
	} else {
		logger = slog.New(handleOpt.NewTextHandler(io.MultiWriter(ioWriters...)))
	}

	slog.SetDefault(logger)
}
