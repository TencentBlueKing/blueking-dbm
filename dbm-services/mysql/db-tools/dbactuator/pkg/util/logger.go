package util

// LoggerErrorStack 在最外层遇到 error 时打印 stack 信息到日志
// err == nil 时不打印
// output 是个 logger，避免在 util 里引入 logger导致循环 import
func LoggerErrorStack(output func(format string, args ...interface{}), err error) {
	if err != nil {
		output("%+v", err)
	}
}
