// Package cmd service cmd
package cmd

import "github.com/spf13/viper"

func init() {
	rootCmd.PersistentFlags().Int("concurrent", 500, "concurrent")
	rootCmd.PersistentFlags().String("mysql_admin_password", "123", "mysql password")
	rootCmd.PersistentFlags().String("mysql_admin_user", "root", "mysql user")

	rootCmd.PersistentFlags().String("proxy_admin_password", "123", "proxy password")
	rootCmd.PersistentFlags().String("proxy_admin_user", "root", "proxy user")

	rootCmd.PersistentFlags().String("sqlserver_admin_password", "123", "sqlserver password")
	rootCmd.PersistentFlags().String("sqlserver_admin_user", "root", "sqlserver user")

	rootCmd.PersistentFlags().Int("port", 8888, "port")

	rootCmd.PersistentFlags().Bool("log_json", true, "json format log")
	rootCmd.PersistentFlags().Bool("log_console", true, "log to console stdout")
	rootCmd.PersistentFlags().Bool("log_debug", true, "display debug log")
	rootCmd.PersistentFlags().Bool("log_source", true, "display source log")

	rootCmd.PersistentFlags().String("tmysqlparser_bin", "/tmysqlparse", "tmysqlparse path")
	rootCmd.PersistentFlags().String("redis_cli_bin", "/redis-cli", "redis-cli path")

	rootCmd.PersistentFlags().String("log_file_dir", "", "log to dir")

	rootCmd.PersistentFlags().String("ca_file", "", "ca file")
	rootCmd.PersistentFlags().String("cert_file", "", "cert file")
	rootCmd.PersistentFlags().String("key_file", "", "key file")
	rootCmd.PersistentFlags().Bool("tls", false, "use tls")

	viper.SetEnvPrefix("DRS")
	viper.AutomaticEnv()
	_ = viper.BindEnv("mysql_admin_user", "MYSQL_ADMIN_USER")
	_ = viper.BindEnv("mysql_admin_password", "MYSQL_ADMIN_PASSWORD")
	_ = viper.BindEnv("proxy_admin_user", "PROXY_ADMIN_USER")
	_ = viper.BindEnv("proxy_admin_password", "PROXY_ADMIN_PASSWORD")
	_ = viper.BindEnv("sqlserver_admin_user", "SQLSERVER_ADMIN_USER")
	_ = viper.BindEnv("sqlserver_admin_password", "SQLSERVER_ADMIN_PASSWORD")
	_ = viper.BindEnv("concurrent", "CONCURRENT")
	_ = viper.BindEnv("port", "PORT")
	_ = viper.BindEnv("tmysqlparser_bin", "TMYSQLPARSER_BIN")
	_ = viper.BindEnv("redis_cli_bin", "REDIS_CLI_BIN")

	_ = viper.BindEnv("log_json", "LOG_JSON")         // bool
	_ = viper.BindEnv("log_console", "LOG_CONSOLE")   // bool
	_ = viper.BindEnv("log_source", "LOG_SOURCE")     // bool
	_ = viper.BindEnv("log_file_dir", "LOG_FILE_DIR") // string
	_ = viper.BindEnv("log_debug", "LOG_DEBUG")

	_ = viper.BindEnv("ca_file", "CA_FILE")
	_ = viper.BindEnv("cert_file", "CERT_FILE")
	_ = viper.BindEnv("key_file", "KEY_FILE")
	_ = viper.BindEnv("tls", "TLS")

	_ = viper.BindPFlags(rootCmd.PersistentFlags())
}
