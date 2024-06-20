package config

import "github.com/spf13/viper"

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
