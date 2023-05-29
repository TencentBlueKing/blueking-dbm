package config

import "github.com/spf13/viper"

// 配置文件格式：
/*
log:
    # 可选: stdout, stderr, /path/to/log/file
    output: /data/logs/myapp/myapp.log
    # 可选: logfmt, json
    formater: logfmt
    # 可选: debug, info, warn, error, fatal, panic
    level: info
    # 100M
    maxsize: 100
    # 保留备份日志文件数
    maxbackups: 3
    # 保留天数
    maxage: 30
    # 启动 level server
    levelserver: false
*/

// Logger TODO
var Logger struct {
	Formater    string
	Level       string
	Output      string
	LocalTime   bool
	TimeFormat  string
	MaxSize     int
	MaxBackups  int
	MaxAge      int
	LevelServer bool
}

// InitLogger TODO
func InitLogger() {
	Logger.Formater = viper.GetString("log.formater")
	Logger.Level = viper.GetString("log.level")
	Logger.Output = viper.GetString("log.output")
	Logger.LocalTime = true
	Logger.TimeFormat = viper.GetString("log.timeformat")
	Logger.MaxSize = viper.GetInt("log.maxsize")
	Logger.MaxBackups = viper.GetInt("log.maxbackups")
	Logger.MaxAge = viper.GetInt("log.maxage")
}
