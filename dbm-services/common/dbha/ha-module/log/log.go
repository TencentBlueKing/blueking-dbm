// Package log TODO
package log

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"time"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"

	"github.com/natefinch/lumberjack"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gorm.io/gorm/logger"
)

// Logger TODO
var Logger *zap.SugaredLogger

// GormLogger use for gorm's db error input
var GormLogger logger.Interface

// Init TODO
func Init(logConf config.LogConfig) error {
	// user ioutil.Discard here to discard gorm's internal error.
	GormLogger = logger.New(log.New(ioutil.Discard, "\r\n", log.LstdFlags), logger.Config{
		SlowThreshold:             200 * time.Millisecond,
		LogLevel:                  logger.Warn,
		IgnoreRecordNotFoundError: false,
		Colorful:                  true,
	})

	// initialize the normal logger
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

	Logger.Info("Logger init ok")
	if isFile {
		err := checkLogFileExist(filepath)
		if err != nil {
			return err
		}
	}
	return nil
}

func getEncoder() zapcore.Encoder {
	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	encoderConfig.EncodeLevel = zapcore.CapitalLevelEncoder
	return zapcore.NewConsoleEncoder(encoderConfig)
}

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

func getStdoutWriter() zapcore.WriteSyncer {
	return zapcore.AddSync(os.Stdout)
}

func getLogLevel(logLevel string) zapcore.Level {
	if logLevel == constvar.LogDebug {
		return zapcore.DebugLevel
	} else if logLevel == constvar.LogInfo {
		return zapcore.InfoLevel
	} else if logLevel == constvar.LogError {
		return zapcore.ErrorLevel
	} else if logLevel == constvar.LogPanic {
		return zapcore.PanicLevel
	} else if logLevel == constvar.LogFatal {
		return zapcore.FatalLevel
	} else {
		return zapcore.DebugLevel
	}
}

func getLogFileConfig(logConf config.LogConfig) (int, int, int) {
	logMaxSize := logConf.LogMaxSize
	if logConf.LogMaxSize == 0 {
		logMaxSize = constvar.LogDefSize
	}

	logMaxAge := logConf.LogMaxAge
	if logMaxAge == 0 {
		logMaxAge = constvar.LogDefAge
	}

	logMaxBackups := logConf.LogMaxBackups
	if logMaxBackups == 0 {
		logMaxBackups = constvar.LogDefBackups
	}

	return logMaxSize, logMaxAge, logMaxBackups
}

func checkLogFilepath(logpath string) (bool, string) {
	if len(logpath) == 0 {
		fmt.Printf("the logfile is not set and log switch to stdout\n")
		return false, ""
	}

	return true, logpath
}

func checkLogFileExist(logpath string) error {
	_, err := os.Stat(logpath)
	if err != nil {
		if os.IsExist(err) {
			fmt.Printf("Log %s is not exist, err:%s\n", logpath, err.Error())
			return err
		}
		fmt.Printf("Log %s check err, err:%s\n", logpath, err.Error())
		return err
	}
	return nil
}
