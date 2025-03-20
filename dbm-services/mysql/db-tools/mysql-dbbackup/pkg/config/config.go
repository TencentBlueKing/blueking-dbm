package config

// BackupConfig the config of dumping backup
// we provide two extra section for logical backup with mysqldump, and they
// are LogicalBackupMysqldump and LogicalLoadMysqldump
type BackupConfig struct {
	Public                 Public                 `ini:"Public"`
	BackupClient           BackupClient           `ini:"BackupClient"`
	LogicalBackup          LogicalBackup          `ini:"LogicalBackup"`
	LogicalLoad            LogicalLoad            `ini:"LogicalLoad"`
	LogicalBackupMysqldump LogicalBackupMysqldump `ini:"LogicalBackupMysqldump"`
	LogicalLoadMysqldump   LogicalLoadMysqldump   `ini:"LogicalLoadMysqldump"`
	PhysicalBackup         PhysicalBackup         `ini:"PhysicalBackup"`
	PhysicalLoad           PhysicalLoad           `ini:"PhysicalLoad"`
}

type LoaderConfig struct {
	//Public               Public               `ini:"Public"`
	LogicalLoad          LogicalLoad          `ini:"LogicalLoad"`
	LogicalLoadMysqldump LogicalLoadMysqldump `ini:"LogicalLoadMysqldump"`
	PhysicalLoad         PhysicalLoad         `ini:"PhysicalLoad"`
}

type LogicalLoaderConfig struct {
	LogicalLoad          LogicalLoad          `ini:"LogicalLoad"`
	LogicalLoadMysqldump LogicalLoadMysqldump `ini:"LogicalLoadMysqldump"`
}

type PhysicalLoaderConfig struct {
	Public       Public       `ini:"Public"`
	PhysicalLoad PhysicalLoad `ini:"PhysicalLoad"`
}
