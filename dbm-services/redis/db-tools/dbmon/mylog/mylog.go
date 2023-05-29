// Package mylog 日志
package mylog

import (
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/robfig/cron/v3"
	"github.com/spf13/viper"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Logger 全局logger
var Logger *zap.Logger

// AdapterLog 适配器logger
var AdapterLog *LogAdapter

// getCurrentDirectory 获取当前二进制程序所在执行路径
func getCurrentDirectory() string {
	dir, err := filepath.Abs(filepath.Dir(os.Args[0]))
	if err != nil {
		log.Panicf(fmt.Sprintf("GetCurrentDirectory failed,os.Args[0]=%s, err: %+v", os.Args[0], err))
		return dir
	}
	dir = strings.Replace(dir, "\\", "/", -1)
	return dir
}

// mkdirIfNotExistsWithPerm 如果目录不存在则创建，并指定文件Perm
func mkdirIfNotExistsWithPerm(dir string, perm os.FileMode) {
	_, err := os.Stat(dir)
	if err == nil {
		return
	}
	if os.IsNotExist(err) == true {
		err = os.MkdirAll(dir, perm)
		if err != nil {
			log.Panicf("MkdirAll fail,err:%v,dir:%s", err, dir)
		}
	}
}

// InitRotateLoger 初始化日志logger
func InitRotateLoger() {
	debug := viper.GetBool("BK_DBMON_DEBUG")
	var level zap.AtomicLevel
	if debug == true {
		level = zap.NewAtomicLevelAt(zapcore.DebugLevel)
	} else {
		level = zap.NewAtomicLevelAt(zapcore.InfoLevel)
	}
	currDir := getCurrentDirectory()
	logDir := filepath.Join(currDir, "logs")
	mkdirIfNotExistsWithPerm(logDir, 0750)

	chownCmd := fmt.Sprintf("chown -R %s.%s %s", consts.MysqlAaccount, consts.MysqlGroup, logDir)
	cmd := exec.Command("bash", "-c", chownCmd)
	cmd.Run()

	cfg := zap.NewProductionConfig()
	cfg.EncoderConfig = zapcore.EncoderConfig{
		MessageKey:     "msg",
		LevelKey:       "level",
		TimeKey:        "time",
		NameKey:        "name",
		CallerKey:      "caller",
		FunctionKey:    "func",
		StacktraceKey:  "stacktrace",
		LineEnding:     zapcore.DefaultLineEnding,
		EncodeLevel:    zapcore.LowercaseLevelEncoder,
		EncodeTime:     zapcore.ISO8601TimeEncoder,
		EncodeDuration: zapcore.SecondsDurationEncoder,
		EncodeCaller:   zapcore.ShortCallerEncoder,
		EncodeName:     zapcore.FullNameEncoder,
	}

	lj := zapcore.AddSync(&lumberjack.Logger{
		Filename:   filepath.Join(logDir, "bk-dbmon.log"),
		MaxSize:    256, // 单个日志文件大小,单位MB
		MaxBackups: 10,  // 最多保存10个文件
		MaxAge:     15,  // 最多保存15天内的日志
		LocalTime:  true,
		Compress:   true,
	})

	core := zapcore.NewCore(zapcore.NewJSONEncoder(cfg.EncoderConfig), zapcore.NewMultiWriteSyncer(lj), level)
	Logger = zap.New(core, zap.AddCaller())

	AdapterLog = &LogAdapter{}
	AdapterLog.Logger = Logger
}

// 无实际作用,仅确保实现了 cron.Logger  接口
var _ cron.Logger = (*LogAdapter)(nil)

// LogAdapter 适配器,目标兼容 go.uber.org/zap.Logger 和 robfig/cron.Logger的接口
type LogAdapter struct {
	*zap.Logger
}

// Error error
func (l *LogAdapter) Error(err error, msg string, keysAndValues ...interface{}) {
	keysAndValues = formatTimes(keysAndValues)
	l.Error(err, fmt.Sprintf(formatString(len(keysAndValues)+2), append([]interface{}{msg, "error", err},
		keysAndValues...)...))
}

// Info info
func (l *LogAdapter) Info(msg string, keysAndValues ...interface{}) {
	keysAndValues = formatTimes(keysAndValues)
	l.Logger.Info(fmt.Sprintf(formatString(len(keysAndValues)), append([]interface{}{msg}, keysAndValues...)...))
}

// formatString returns a logfmt-like format string for the number of
// key/values.
func formatString(numKeysAndValues int) string {
	var sb strings.Builder
	sb.WriteString("%s")
	if numKeysAndValues > 0 {
		sb.WriteString(", ")
	}
	for i := 0; i < numKeysAndValues/2; i++ {
		if i > 0 {
			sb.WriteString(", ")
		}
		sb.WriteString("%v=%v")
	}
	return sb.String()
}

// formatTimes formats any time.Time values as RFC3339.
func formatTimes(keysAndValues []interface{}) []interface{} {
	var formattedArgs []interface{}
	for _, arg := range keysAndValues {
		if t, ok := arg.(time.Time); ok {
			arg = t.Format(time.RFC3339)
		}
		formattedArgs = append(formattedArgs, arg)
	}
	return formattedArgs
}
