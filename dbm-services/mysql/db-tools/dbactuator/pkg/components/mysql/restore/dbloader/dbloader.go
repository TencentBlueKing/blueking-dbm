// Package dbloader TODO
package dbloader

// DBBackupLoader dbbackup loadbackup sub-command
type DBBackupLoader interface {
	CreateConfigFile() error
	PreLoad() error
	Load() error
}
