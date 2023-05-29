// Package config 配置
package config

import (
	"os"
	"path/filepath"

	"github.com/spf13/viper"
)

// RuntimeConfig 运行配置
var RuntimeConfig *runtimeConfig

// LogConfig 日志配置
var LogConfig *logConfig

type runtimeConfig struct {
	Concurrent         int
	MySQLAdminUser     string
	MySQLAdminPassword string
	ProxyAdminUser     string
	ProxyAdminPassword string
	Port               int
	ParserBin          string
	CAFile             string
	CertFile           string
	KeyFile            string
	TLS                bool
}

type logConfig struct {
	Console    bool   `yaml:"console"`
	LogFileDir string `yaml:"log_file_dir"`
	Debug      bool   `yaml:"debug"`
	Source     bool   `yaml:"source"`
	Json       bool   `yaml:"json"`
}

// InitConfig 初始化配置
func InitConfig() {
	RuntimeConfig = &runtimeConfig{
		Concurrent:         viper.GetInt("concurrent"),
		MySQLAdminUser:     viper.GetString("mysql_admin_user"),
		MySQLAdminPassword: viper.GetString("mysql_admin_password"),
		ProxyAdminUser:     viper.GetString("proxy_admin_user"),
		ProxyAdminPassword: viper.GetString("proxy_admin_password"),
		Port:               viper.GetInt("port"),
		ParserBin:          viper.GetString("tmysqlparser_bin"),
		TLS:                viper.GetBool("tls"),
		CAFile:             viper.GetString("ca_file"),
		CertFile:           viper.GetString("cert_file"),
		KeyFile:            viper.GetString("key_file"),
	}

	if !filepath.IsAbs(RuntimeConfig.ParserBin) {
		executable, _ := os.Executable()
		RuntimeConfig.ParserBin = filepath.Join(filepath.Dir(executable), RuntimeConfig.ParserBin)
	}

	LogConfig = &logConfig{
		Console:    viper.GetBool("log_console"),
		LogFileDir: viper.GetString("log_file_dir"),
		Debug:      viper.GetBool("log_debug"),
		Source:     viper.GetBool("log_source"),
		Json:       viper.GetBool("log_json"),
	}
}
