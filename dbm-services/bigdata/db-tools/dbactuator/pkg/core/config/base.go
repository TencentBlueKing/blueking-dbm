package config

// GRPC TODO
var GRPC struct {
	Addr string `mapstructure:"addr"`
	Port int    `mapstructure:"port"`
}

// HTTP TODO
var HTTP struct {
	Addr string `mapstructure:"addr"`
	Port int    `mapstructure:"port"`
}

// BKCONFIG TODO
var BKCONFIG struct {
	Addr   string `mapstructure:"addr"`
	Path   string `mapstructure:"path"`
	Method string `mapstructure:"method"`
}
