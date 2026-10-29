package config

// LogConfig 日志配置结构
type LogConfig struct {
	Console    bool    `yaml:"console" json:"console"`
	LogFileDir *string `yaml:"log_file_dir" json:"log_file_dir"`
	Debug      bool    `yaml:"debug" json:"debug"`
	Source     bool    `yaml:"source" json:"source"`
	Json       bool    `yaml:"json" json:"json"`
}
