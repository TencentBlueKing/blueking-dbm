package logger_test

import (
	"bk-dbconfig/pkg/core/logger"
	"bk-dbconfig/pkg/core/logger/zap"
)

// 初始化日志
func ExampleInitLog() {
	// 用指定日志初始化
	zapLogger := zap.New()
	logger.InitLogger(zapLogger)
}

func ExampleInfo() {
	msg := "something happened"
	// time="2020-04-17T09:34:13+08:00" level=info msg="Message: something happened" hostname=localhost src="mod1/myapp.go:20"
	fields := map[string]interface{}{"field1": "value1"}
	logger.WithFields(fields).Info("Message: %s", msg)
}
