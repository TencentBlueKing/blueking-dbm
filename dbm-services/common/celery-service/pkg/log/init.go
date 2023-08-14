package log

import (
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/iancoleman/strcase"
	"golang.org/x/exp/slog"
	"gopkg.in/natefinch/lumberjack.v2"

	"celery-service/pkg/config"
)

var toConsole bool

func Init(logToConsole bool) {
	toConsole = logToConsole
}

func GetLogger(name string) *slog.Logger {
	name = strcase.ToSnake(name)

	var filePath string
	if name == "root" {
		filePath = filepath.Join(config.LogDir, fmt.Sprintf("%s.log", config.Executable))
	} else {
		filePath = filepath.Join(config.LogDir, name, fmt.Sprintf("%s.log", name))
	}

	fileWriter := &lumberjack.Logger{
		Filename:   filePath,
		MaxSize:    100,
		MaxAge:     30,
		MaxBackups: 50,
	}

	var logWriter io.Writer
	if toConsole {
		logWriter = io.MultiWriter(fileWriter, os.Stdout)
	} else {
		logWriter = fileWriter
	}

	return slog.New(
		slog.NewTextHandler(
			logWriter,
			&slog.HandlerOptions{
				AddSource: true,
				Level:     slog.LevelDebug,
			},
		),
	).With("name", name)
}
