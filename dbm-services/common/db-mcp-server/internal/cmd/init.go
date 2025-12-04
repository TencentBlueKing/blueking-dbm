package cmd

import (
	"github.com/spf13/viper"
)

func init() {
	rootCmd.PersistentFlags().String(
		"bind-address",
		"0.0.0.0:80",
		"The IP address on which to listen for the --port port.",
	)
	rootCmd.PersistentFlags().String("mcp-backend-base-url", "", "")
	//rootCmd.PersistentFlags().String("bk-app-code", "", "")
	//rootCmd.PersistentFlags().String("bk-app-secret", "", "")
	//rootCmd.PersistentFlags().BoolVarP(&config.SkipAuthCheck, "skip-auth-check", "s", false, "")

	_ = rootCmd.MarkFlagRequired("mcp-backend-base-url")
	//_ = rootCmd.MarkFlagRequired("bk-app-code")
	//_ = rootCmd.MarkFlagRequired("bk-app-secret")

	viper.SetEnvPrefix("MCP")
	viper.AutomaticEnv()
	_ = viper.BindEnv("bind-address", "BIND_ADDRESS")
	_ = viper.BindEnv("mcp-backend-base-url", "MCP_BACKEND_BASE_URL")
	//_ = viper.BindEnv("bk-app-code", "BK_APP_CODE")
	//_ = viper.BindEnv("bk-app-secret", "BK_APP_SECRET")

	_ = viper.BindPFlags(rootCmd.PersistentFlags())
}
