package config

// LogConfig TODO
type LogConfig struct {
	Console    bool    `yaml:"console"`
	LogFileDir *string `yaml:"log_file_dir"`
	Debug      bool    `yaml:"debug"`
	Source     bool    `yaml:"source"`
	Json       bool    `yaml:"json"`
}
