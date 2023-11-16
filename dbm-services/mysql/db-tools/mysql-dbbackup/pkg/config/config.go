package config

// BackupConfig the config of dumping backup
type BackupConfig struct {
	Public         Public         `ini:"Public"`
	BackupClient   BackupClient   `ini:"BackupClient"`
	LogicalBackup  LogicalBackup  `ini:"LogicalBackup"`
	LogicalLoad    LogicalLoad    `ini:"LogicalLoad"`
	PhysicalBackup PhysicalBackup `ini:"PhysicalBackup"`
	PhysicalLoad   PhysicalLoad   `ini:"PhysicalLoad"`
}
