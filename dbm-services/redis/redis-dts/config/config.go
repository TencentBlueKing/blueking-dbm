// Package config TODO
package config

import (
	"github.com/spf13/viper"
)

// InitConfig 加载配置文件
func InitConfig(cfgFile *string) {

	if *cfgFile != "" {
		viper.SetConfigFile(*cfgFile)
	} else {
		viper.AddConfigPath("./")
		viper.SetConfigType("yaml")
		viper.SetConfigName("config")
	}

	if err := viper.ReadInConfig(); err != nil {
		panic(err)
	}
	viper.WatchConfig() // auto reload config file when config file changed
}
