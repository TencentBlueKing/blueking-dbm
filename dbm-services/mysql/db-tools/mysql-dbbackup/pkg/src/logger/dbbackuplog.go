// Package logger TODO
package logger

import (
	"os"
	"path/filepath"

	"github.com/pkg/errors"
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
	logFile := filepath.Join(logDir, logFileName)
	// lumberjack 强制写死的新文件权限是 0644，但会继承已经存在的文件权限，所以提前创建文件
	if f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644); err != nil {
		return errors.Wrap(err, "open log file")
	} else {
		f.Close()
	}
	Log.SetOutput(&lumberjack.Logger{
		Filename:   logFile,
		MaxSize:    50, // megabytes
		MaxBackups: 3,
		MaxAge:     28,    // days
		Compress:   false, // disabled by default
	})
	return nil
}
