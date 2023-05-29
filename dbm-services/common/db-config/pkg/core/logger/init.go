package logger

import (
	"bk-dbconfig/pkg/core/config"
	"bk-dbconfig/pkg/core/logger/zap"
)

func init() {
	// DefaultLogger = zap.New()
}

// Init 用于在程序初始化时，确保import了模块，以执行注册的初始化方法。
func Init() {
	config.InitLogger()
	DefaultLogger = zap.New()
}
