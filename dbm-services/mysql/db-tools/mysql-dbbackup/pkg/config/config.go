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

/*
// LogicalBackupCnf Logical Backup BackupConfig
type LogicalBackupCnf struct {
	Public        Public        `ini:"Public" validate:"required"`
	LogicalBackup LogicalBackup `ini:"LogicalBackup" validate:"required"`
}

// LogicalLoadCnf Logical Load BackupConfig
type LogicalLoadCnf struct {
	LogicalBackup LogicalBackup `ini:"LogicalBackup" validate:"required"`
}

// PhysicalBackupCnf Physical Backup BackupConfig
type PhysicalBackupCnf struct {
	Public         Public         `ini:"Public" validate:"required"`
	PhysicalBackup PhysicalBackup `ini:"PhysicalBackup" validate:"required"`
}

// PhysicalLoadCnf Physical Load BackupConfig
type PhysicalLoadCnf struct {
	PhysicalLoad PhysicalLoad `ini:"PhysicalLoad" validate:"required"`
}
*/
