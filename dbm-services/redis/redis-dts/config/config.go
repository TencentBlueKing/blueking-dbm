// Package config TODO
package config

import (
	"flag"

	"github.com/spf13/viper"
)

var cfgFile = flag.String("config-file", "./config.yaml", "Input your config file")

// InitConfig 加载配置文件
func InitConfig() {
	flag.Parse()

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
