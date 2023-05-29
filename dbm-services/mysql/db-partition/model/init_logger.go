package model

import (
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/spf13/viper"
	"gopkg.in/natefinch/lumberjack.v2"
)

// InitLog 程序日志初始化
func InitLog() {
	var logLevel = new(slog.LevelVar)
	logLevel.Set(slog.LevelInfo)
	if strings.ToLower(strings.TrimSpace(viper.GetString("log.level"))) == "debug" {
		logLevel.Set(slog.LevelDebug)
	}
	var logger *slog.TextHandler
	logger = slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: logLevel, AddSource: true})
	logPath := strings.TrimSpace(viper.GetString("log.path"))
	if logPath != "" {
		logger = slog.NewTextHandler(NewWriter(logPath), &slog.HandlerOptions{Level: logLevel, AddSource: true})
	}
	slog.SetDefault(slog.New(logger))
}

// NewWriter TODO
func NewWriter(path string) io.Writer {
	return io.MultiWriter(os.Stdout, &lumberjack.Logger{
		Filename:   path,
		MaxSize:    viper.GetInt("log.max_size"),
		MaxAge:     viper.GetInt("log.max_age"),
		MaxBackups: viper.GetInt("log.max_backups"),
		LocalTime:  true,
	})
}
