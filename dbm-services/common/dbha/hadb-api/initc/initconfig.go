package initc

// GlobalConfig TODO
var GlobalConfig *Config

// Config struct generate by https://zhwt.github.io/yaml-to-go/
type Config struct {
	HadbInfo     HadbInfo     `yaml:"hadbInfo"`
	ServerInfo   ServerInfo   `yaml:"serverInfo"`
	NetInfo      NetInfo      `yaml:"netInfo"`
	LogInfo      LogInfo      `yaml:"logInfo"`
	TimezoneInfo TimezoneInfo `yaml:"timezone"`
}

// HadbInfo TODO
type HadbInfo struct {
	Host     string `yaml:"host"`
	Port     int    `yaml:"port"`
	Db       string `yaml:"db"`
	User     string `yaml:"user"`
	Password string `yaml:"password"`
	Charset  string `yaml:"charset"`
}

// ServerInfo TODO
type ServerInfo struct {
	Name string `yaml:"name"`
}

// NetInfo TODO
type NetInfo struct {
	Port string `yaml:"port"`
}

// LogInfo TODO
type LogInfo struct {
	LogPath       string `yaml:"logPath"`
	LogLevel      string `yaml:"logLevel"`
	LogMaxSize    int    `yaml:"logMaxsize"`
	LogMaxBackups int    `yaml:"logMaxbackups"`
	LogMaxAge     int    `yaml:"logMaxage"`
	LogCompress   bool   `yaml:"logCompress"`
}

// TimezoneInfo support timezone configure
type TimezoneInfo struct {
	Local string `yaml:"local"`
}
