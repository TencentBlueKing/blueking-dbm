package config

import (
	"os"
	"path/filepath"

	"github.com/spf13/viper"
	"gopkg.in/yaml.v2"
)

var RuntimeConfig *runtimeConfig
var MetaInfo *KafkaMeta

func init() {
	RuntimeConfig = &runtimeConfig{}
	MetaInfo = &KafkaMeta{}
}

func InitConfig() {
	configPath := viper.GetString("config")
	if !filepath.IsAbs(configPath) {
		cwd, err := os.Getwd()
		if err != nil {
			panic(err)
		}

		configPath = filepath.Join(cwd, configPath)
		viper.Set("config", configPath)
	}

	content, err := os.ReadFile(configPath)
	if err != nil {
		panic(err)
	}

	err = yaml.Unmarshal(content, RuntimeConfig)
	if err != nil {
		panic(err)
	}
}
