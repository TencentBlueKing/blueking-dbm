package config

import "github.com/spf13/viper"

var Config *config
var SkipAuthCheck bool

type config struct {
	BindAddress       string `json:"bind-address"`
	MCPBackendBaseURL string `json:"mcp-backend-base-url"`
	BKAppCode         string `json:"bk-app-code"`
	BKAppSecret       string `json:"bk-app-secret"`
}

func InitConfig() {
	Config = &config{
		BindAddress:       viper.GetString("bind-address"),
		MCPBackendBaseURL: viper.GetString("mcp-backend-base-url"),
		BKAppCode:         viper.GetString("bk-app-code"),
		BKAppSecret:       viper.GetString("bk-app-secret"),
	}
}
