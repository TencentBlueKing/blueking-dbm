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
	// Pool 连接池配置，缺省或为 0 时使用默认值
	Pool PoolInfo `yaml:"pool"`
}

// PoolInfo 数据库连接池配置，所有字段均可缺省，缺省时走默认值
type PoolInfo struct {
	// MaxOpenConns 最大打开连接数，<=0 时使用默认值 50
	MaxOpenConns int `yaml:"maxOpenConns"`
	// MaxIdleConns 最大空闲连接数，<=0 时使用默认值 10
	MaxIdleConns int `yaml:"maxIdleConns"`
	// ConnMaxLifetimeSec 连接最大存活时间(秒)，<=0 时使用默认值 1800(30 分钟)
	ConnMaxLifetimeSec int `yaml:"connMaxLifetimeSec"`
	// ConnMaxIdleTimeSec 连接最大空闲时间(秒)，<=0 时使用默认值 300(5 分钟)
	ConnMaxIdleTimeSec int `yaml:"connMaxIdleTimeSec"`
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
