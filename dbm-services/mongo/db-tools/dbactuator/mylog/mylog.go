// Package mylog 便于全局日志操作
package mylog

import (
	"os"

	"dbm-services/common/go-pubpkg/logger"
)

// Logger 和 jobruntime.Logger 是同一个 logger
var Logger *logger.Logger

// SetDefaultLogger 设置默认logger
func SetDefaultLogger(log *logger.Logger) {
	Logger = log
}

// UnitTestInitLog 单元测试初始化Logger
func UnitTestInitLog() {
	extMap := map[string]string{
		"uid":        "1111",
		"node_id":    "localhost",
		"root_id":    "2222",
		"version_id": "3333",
	}
	log01 := logger.New(os.Stdout, true, logger.InfoLevel, extMap)
	log01.Sync()
	SetDefaultLogger(log01)
}
