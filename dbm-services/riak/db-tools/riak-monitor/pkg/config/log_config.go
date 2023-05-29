package config

// LogConfig 日志配置
type LogConfig struct {
	// 是否console输出
	Console bool `yaml:"console"`
	// 位置
	LogFileDir *string `yaml:"log_file_dir"`
	Debug      bool    `yaml:"debug"`
	// 是否打印日志源头信息
	Source bool `yaml:"source"`
	Json   bool `yaml:"json"`
}
