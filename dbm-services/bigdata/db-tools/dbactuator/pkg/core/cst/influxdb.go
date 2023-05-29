package cst

const (
	// DefaultInfluxdbDataDir TODO
	DefaultInfluxdbDataDir = "/data/influxdbdata"
	// DefaultInfluxdbPort TODO
	DefaultInfluxdbPort = 9092 // 默认端口
	// DefaultInfluxdbEnv TODO
	DefaultInfluxdbEnv = "/data/influxdbenv" // kafka安装包存放目录
	// DefaultInfluxdbLogDir TODO
	DefaultInfluxdbLogDir = "/data/influxdblog"
	// DefaultInfluxdbDir TODO
	DefaultInfluxdbDir = DefaultInfluxdbEnv + "/influxdb"
	// DefaultInfluxdbSupervisorConf TODO
	DefaultInfluxdbSupervisorConf = DefaultInfluxdbEnv + "/supervisor/conf"
)
