package config

import (
	"strings"

	"github.com/spf13/viper"
)

var Config *config

//var WithAuthCheck bool

type config struct {
	BindAddress       string `json:"bind-address"`
	MCPBackendBaseURL string `json:"mcp-backend-base-url"`
	BKAppCode         string `json:"bk-app-code"`
	BKAppSecret       string `json:"bk-app-secret"`
	BKMCPUsername     string `json:"bk-mcp-username"`
	WithAuthCheck     *bool  `json:"with-auth-check"`
}

func InitConfig() {
	withAuthCheck := viper.GetBool("with-auth-check")
	Config = &config{
		BindAddress:       viper.GetString("bind-address"),
		MCPBackendBaseURL: viper.GetString("mcp-backend-base-url"),
		BKAppCode:         viper.GetString("bk-app-code"),
		BKAppSecret:       viper.GetString("bk-app-secret"),
		BKMCPUsername:     strings.TrimSpace(viper.GetString("bk-mcp-username")),
		WithAuthCheck:     &withAuthCheck,
	}
	Config.BKMCPUsername = "admin"
}
