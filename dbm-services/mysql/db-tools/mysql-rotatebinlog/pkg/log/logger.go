package log

import (
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"gopkg.in/natefinch/lumberjack.v2"

	"dbm-services/common/go-pubpkg/logger"
)

// InitLogger TODO
func InitLogger() error {
	executable, _ := os.Executable()
	executeDir := filepath.Dir(executable)
	if err := os.Chdir(executeDir); err != nil {
		os.Stderr.WriteString(err.Error())
		os.Exit(1)
	}
	logFileDir := filepath.Join(executeDir, "logs")
	_ = os.MkdirAll(logFileDir, 0755)
	fileName := filepath.Join(logFileDir, "rotatebinlog.log")
	fiw := &lumberjack.Logger{
		Filename:   fileName,
		MaxAge:     7,
		MaxSize:    100,
		MaxBackups: 7,
		Compress:   false,
	}

	extMap := map[string]string{}
	l := logger.New(fiw, true, logger.InfoLevel, extMap)
	logger.ResetDefault(l)
	logger.Sync()
	return nil
}

func InitLogger2(cfg *LogConfig) {
	executable, _ := os.Executable()
	//executableName := filepath.Base(executable)
	executableDir := filepath.Dir(executable)

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

		logFile := filepath.Join(*cfg.LogFileDir, "rotatebinlog.log")
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
			MaxAge:   7,
			//MaxBackups: 2,
			Compress: true,
		})
	}

	handleOpt := slog.HandlerOptions{AddSource: cfg.Source}
	if cfg.Debug {
		handleOpt.Level = slog.LevelDebug
	} else {
		handleOpt.Level = slog.LevelInfo
	}

	var logger *slog.Logger
	if cfg.Json {
		logger = slog.New(slog.NewJSONHandler(io.MultiWriter(ioWriters...), &handleOpt))
	} else {
		logger = slog.New(slog.NewTextHandler(io.MultiWriter(ioWriters...), &handleOpt))
	}

	slog.SetDefault(logger)
}
