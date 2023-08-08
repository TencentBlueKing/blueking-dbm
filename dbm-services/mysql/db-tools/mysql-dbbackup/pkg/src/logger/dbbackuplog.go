// Package logger TODO
package logger

import (
	"os"
	"path/filepath"

	"github.com/sirupsen/logrus"
	"gopkg.in/natefinch/lumberjack.v2"

	"dbm-services/common/go-pubpkg/cmutil"
)

// Log TODO
var Log *logrus.Logger

const DefaultLogFileName = "dbbackup.log"

// InitLog Initialize dbbackupLog
func InitLog(logFileName string) (err error) {
	Log = logrus.New()
	Log.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
	})
	// Log.Out = os.Stdout
	executable, _ := os.Executable()
	logDir := filepath.Join(filepath.Dir(executable), "logs")
	if !cmutil.IsDirectory(logDir) {
		_ = os.Mkdir(logDir, 0755)
	}
	if logFileName == "" {
		logFileName = DefaultLogFileName
	}
	Log.SetOutput(&lumberjack.Logger{
		Filename:   filepath.Join(logDir, logFileName),
		MaxSize:    50, // megabytes
		MaxBackups: 3,
		MaxAge:     28,    // days
		Compress:   false, // disabled by default
	})
	return nil
}
