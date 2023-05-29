// Package log TODO
package log

import (
	"fmt"
	"os"
	"path/filepath"

	"dbm-services/common/dbha/hadb-api/initc"
	"dbm-services/common/dbha/hadb-api/util"

	"github.com/natefinch/lumberjack"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// Logger TODO
var Logger *zap.SugaredLogger

// InitLog TODO
// Init init log module
func InitLog(logConf initc.LogInfo) {
	// initilize the normal logger
	level := getLogLevel(logConf.LogLevel)
	isFile, filepath := checkLogFilepath(logConf.LogPath)
	var writeSyncer zapcore.WriteSyncer
	if isFile {
		logMaxSize, logMaxAge, logMaxBackups := getLogFileConfig(logConf)
		fmt.Printf("log FILE parameter: filePath=%s,maxSize=%d,maxAge=%d,maxBackups=%d,compress=%v\n",
			filepath, logMaxSize, logMaxAge, logMaxBackups, logConf.LogCompress)
		writeSyncer = getLogFileWriter(filepath, logMaxSize,
			logMaxBackups, logMaxAge, logConf.LogCompress)
	} else {
		fmt.Printf("log stdout\n")
		writeSyncer = getStdoutWriter()
	}

	encoder := getEncoder()
	core := zapcore.NewCore(encoder, writeSyncer, level)
	rowLogger := zap.New(core, zap.AddCaller())
	Logger = rowLogger.Sugar()
}

// getEncoder get log encoder
func getEncoder() zapcore.Encoder {
	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	encoderConfig.EncodeLevel = zapcore.CapitalLevelEncoder
	return zapcore.NewConsoleEncoder(encoderConfig)
}

// getLogFileWriter support log write to file
func getLogFileWriter(filename string, logMaxSize int,
	logMaxBackups int, logMaxAge int, compress bool) zapcore.WriteSyncer {
	lumberJackLogger := &lumberjack.Logger{
		Filename:   filename,
		MaxSize:    logMaxSize,
		MaxBackups: logMaxBackups,
		MaxAge:     logMaxAge,
		Compress:   compress,
	}
	return zapcore.AddSync(lumberJackLogger)
}

// getStdoutWriter support log write to stdout
func getStdoutWriter() zapcore.WriteSyncer {
	return zapcore.AddSync(os.Stdout)
}

// getLogLevel get the value of log level
func getLogLevel(logLevel string) zapcore.Level {
	switch logLevel {
	case util.LOG_DEBUG:
		return zapcore.DebugLevel
	case util.LOG_INFO:
		return zapcore.InfoLevel
	case util.LOG_ERROR:
		return zapcore.ErrorLevel
	case util.LOG_PANIC:
		return zapcore.PanicLevel
	case util.LOG_FATAL:
		return zapcore.FatalLevel
	default:
		return zapcore.DebugLevel
	}
}

// getLogFileConfig get the value of log parameter
func getLogFileConfig(logConf initc.LogInfo) (int, int, int) {
	logMaxSize := logConf.LogMaxSize
	if logConf.LogMaxSize == 0 {
		logMaxSize = util.LOG_DEF_SIZE
	}

	logMaxAge := logConf.LogMaxAge
	if logMaxAge == 0 {
		logMaxAge = util.LOG_DEF_AGE
	}

	logMaxBackups := logConf.LogMaxBackups
	if logMaxBackups == 0 {
		logMaxBackups = util.LOG_DEF_BACKUPS
	}

	return logMaxSize, logMaxAge, logMaxBackups
}

// checkLogFilepath check the log path is exist or not
func checkLogFilepath(logpath string) (bool, string) {
	if len(logpath) == 0 {
		fmt.Printf("the logfile is not set and log switch to stdout\n")
		return false, ""
	}

	fpath := filepath.Dir(logpath)
	_, err := os.Stat(fpath)
	if err != nil && os.IsNotExist(err) {
		fmt.Printf("the father path:%s is not exist\n", fpath)
		return false, ""
	}
	return true, logpath
}
