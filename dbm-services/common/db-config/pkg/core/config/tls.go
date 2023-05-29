package config

// 配置文件格式：
/*
tls:
 ca: configs/certs/ca.crt
 server_name: server.example.com
 server_cert: configs/certs/server.crt
 server_key: configs/certs/server.key
 auth: true
 client_cert: configs/certs/client.crt
 client_key: configs/certs/client.key
*/

// Tls TODO
var Tls struct {
	CA         string `mapstructure:"ca"`
	ServerName string `mapstructure:"server_name"`
	ServerCert string `mapstructure:"server_cert"`
	ServerKey  string `mapstructure:"server_key"`
	Auth       bool   `mapstructure:"auth"`
	ClientCert string `mapstructure:"client_cert"`
	ClientKey  string `mapstructure:"client_key"`
}
