package logrus

import (
	"bk-dbconfig/pkg/core/config"
	"os"
	"path"

	"github.com/sirupsen/logrus"
)

var (
	_LOGHOSTNAME = ""
)

// New TODO
func New() *logrusLogger {
	// 初始化全局变量
	_LOGHOSTNAME, _ = os.Hostname()

	switch config.Logger.Formater {
	case "json":
		logrus.SetFormatter(&logrus.JSONFormatter{})
	default:
		logrus.SetFormatter(&logrus.TextFormatter{})
	}

	switch config.Logger.Output {
	case "stdout":
		logrus.SetOutput(os.Stdout)
	default:
		dir := path.Dir(config.Logger.Output)
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			err := os.MkdirAll(dir, os.ModePerm)
			if err != nil {
				logrus.Panicf("Failed to log to file: %s", config.Logger.Output)
			}
		}

		file, err := os.OpenFile(config.Logger.Output, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
		if err != nil {
			logrus.Panicf("Failed to log to file: %s", config.Logger.Output)
		}

		logrus.SetOutput(file)
	}

	switch config.Logger.Level {
	case "debug":
		logrus.SetLevel(logrus.DebugLevel)
	case "info":
		logrus.SetLevel(logrus.InfoLevel)
	case "warning", "warn":
		logrus.SetLevel(logrus.WarnLevel)
	case "error":
		logrus.SetLevel(logrus.ErrorLevel)
	case "fatal":
		logrus.SetLevel(logrus.FatalLevel)
	case "panic":
		logrus.SetLevel(logrus.PanicLevel)
	}

	return NewLogger()
}
