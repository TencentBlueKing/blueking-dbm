package config

// LogConfig 日志配置结构
type LogConfig struct {
	Console    bool    `yaml:"console"`
	LogFileDir *string `yaml:"log_file_dir"`
	Debug      bool    `yaml:"debug"`
	Source     bool    `yaml:"source"`
	Json       bool    `yaml:"json"`
}
