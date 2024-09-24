// Package logger TODO
package logger

import (
	"os"
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"github.com/spf13/viper"
	"gopkg.in/natefinch/lumberjack.v2"

	"dbm-services/common/go-pubpkg/cmutil"
)

// Log TODO
var Log *logrus.Logger

const DefaultLogFileName = "dbbackup.log"

// GetLogDir get log dir
func GetLogDir() string {
	logDir := viper.GetString("log-dir")
	if logDir == "" {
		executable, _ := os.Executable()
		logDir = filepath.Join(filepath.Dir(executable), "logs")
	}
	return logDir
}

// InitLog Initialize dbbackupLog
// 如果 logDir 为空，则 log记录到 dbbackup/logs 下
// 如果 logFileName 包含相对目录，则根据在命令当前目录下创建相对目录
// 如果 logFileName 包含绝对目录，则以绝对目录的 log file 来记录
func InitLog(logFileName string) (err error) {
	Log = logrus.New()
	Log.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
	})
	if logFileName == "" {
		logFileName = DefaultLogFileName
	}
	logDir := GetLogDir()
	if !cmutil.IsDirectory(logDir) {
		_ = os.Mkdir(logDir, 0755)
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
