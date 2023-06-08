// Package logger TODO
package logger

import (
	"os"
	"path/filepath"

	"github.com/sirupsen/logrus"
	"gopkg.in/natefinch/lumberjack.v2"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/go-pubpkg/cmutil"
)

// Log TODO
var Log *logrus.Logger

// InitLog Initialize dbbackupLog
func InitLog() (err error) {
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
	Log.SetOutput(&lumberjack.Logger{
		Filename:   filepath.Join(logDir, "dbbackup.log"),
		MaxSize:    50, // megabytes
		MaxBackups: 3,
		MaxAge:     28,    // days
		Compress:   false, // disabled by default
	})
	return nil
}
