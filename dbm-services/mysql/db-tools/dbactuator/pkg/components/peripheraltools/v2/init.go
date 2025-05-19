package peripheraltools

const (
	DepartDBAToolKit         = "dba-toolkit"
	DepartMySQLCrond         = "mysql-crond"
	DepartMySQLMonitor       = "mysql-monitor"
	DepartMySQLDBBackup      = "mysql-dbbackup"
	DepartMySQLRotateBinlog  = "rotate-binlog"
	DepartMySQLTableChecksum = "mysql-checksum"
	DepartExporter           = "exporter"
)

type LogConfig struct {
	Console    bool    `yaml:"console"`
	LogFileDir *string `yaml:"log_file_dir"`
	Debug      bool    `yaml:"debug"`
	Source     bool    `yaml:"source"`
	Json       bool    `yaml:"json"`
}
