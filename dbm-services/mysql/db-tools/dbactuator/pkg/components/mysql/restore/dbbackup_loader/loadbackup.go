// Package dbloader TODO
package dbbackup_loader

// DBBackupLoader dbbackup loadbackup sub-command
type DBBackupLoader interface {
	CreateConfigFile() error
	PreLoad() error
	Load() error
	PostLoad() error
}
