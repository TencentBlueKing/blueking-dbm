// Package dbloader TODO
package dbloader

// DBBackupLoader dbbackup -loadbackup
type DBBackupLoader interface {
	CreateConfigFile() error
	PreLoad() error
	Load() error
}
