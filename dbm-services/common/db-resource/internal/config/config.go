// Package config TODO
package config

import (
	"log"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/viper"
)

// AppConfig TODO
var AppConfig Config

// Config TODO
type Config struct {
	Gormlog          bool              `yaml:"gormlog"`
	ListenAddress    string            `yaml:"listenAddress"`
	Db               Db                `yaml:"db"`
	CmdbDb           Db                `yaml:"cmdb_db" mapstructure:"cmdb_db"`
	LoggerConfig     LoggerConfig      `yaml:"loggerConfig"`
	BkSecretConfig   BkSecretConfig    `yaml:"bkSecretConfig"`
	Redis            Redis             `yaml:"redis"`
	CloudCertificate *CloudCertificate `yaml:"cloudCertificate"`
	//	dbmeta: http://bk-dbm
	DbMeta string `json:"dbmeta"`
}

// Db TODO
type Db struct {
	Name     string `yaml:"name"`
	Addr     string `yaml:"addr"`
	UserName string `yaml:"username"`
	PassWord string `yaml:"password"`
}

// LoggerConfig 日志配置
type LoggerConfig struct {
	LogWriters string `yaml:"logWriters"` // file,stdout
	LogLevel   string `yaml:"logLevel"`
	LogFile    string `yaml:"logfile"`
}

// BkSecretConfig TODO
type BkSecretConfig struct {
	BkAppCode   string `yaml:"bk_app_code" mapstructure:"bk_app_code"`
	BKAppSecret string `yaml:"bk_app_secret" mapstructure:"bk_app_secret"`
	BkUserName  string `yaml:"bk_username" mapstructure:"bk_username"`
	BkBaseUrl   string `yaml:"bk_base_url" mapstructure:"bk_base_url"`
	GseBaseUrl  string `yaml:"gse_base_url" mapstructure:"gse_base_url"`
}

// Redis TODO
type Redis struct {
	Addr     string `yaml:"addr"`
	Password string `yaml:"password"`
}

// CloudCertificate TODO
type CloudCertificate struct {
	// cloud vendor reserved field
	CloudVendor string `yaml:"cloud_vendor" mapstructure:"cloud_vendor"`
	SecretId    string `yaml:"secret_id" mapstructure:"secret_id"`
	SecretKey   string `yaml:"secret_key" mapstructure:"secret_key"`
} // load configuration file

func init() {
	log.Println("init config")
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("$HOME/conf")
	viper.AddConfigPath("./conf")
	viper.AddConfigPath("./")
	if err := viper.ReadInConfig(); err != nil {
		logger.Fatal("failed to read configuration file:%v", err)
	}
	if err := viper.Unmarshal(&AppConfig); err != nil {
		logger.Fatal("unmarshal configuration failed: %v", err)
	}
}
