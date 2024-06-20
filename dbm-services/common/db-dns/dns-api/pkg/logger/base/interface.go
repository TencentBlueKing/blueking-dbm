package base

// ILogger TODO
type ILogger interface {
	ImpleLogger()
	Init()
	Debug(format string, args ...interface{})
	Info(format string, args ...interface{})
	Warn(format string, args ...interface{})
	Error(format string, args ...interface{})
	Fatal(format string, args ...interface{})
	Panic(format string, args ...interface{})
	WithFields(mapFields map[string]interface{}) ILogger
}
