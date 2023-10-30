// Package staticembed TODO
package staticembed

import "embed"

const (
	// SysInitScriptFileName TODO
	SysInitScriptFileName = "sysinit.ps1"
	// InitSqlServerFileName TODO
	InitSqlServerFileName = "init_sqlserver.ps1"
	// MonitorFileName TODO
	MonitorFileName = "01_monitor.sql"
	// BackupFileName TODO
	BackupFileName = "02_backup.sql"
	// AutoSwitchFileName TODO
	AutoSwitchFileName = "03_auto_switch.sql"
	// SqlSettingFileName TODO
	SqlSettingFileName = "04_sqlsetting.sql"
	// TestFileName TODO
	TestFileName = "test.sql"
)

// SysInitScript TODO
//
//go:embed sysinit.ps1
var SysInitScript embed.FS

// InitSqlServer TODO
//
//go:embed init_sqlserver.ps1
var InitSqlServer embed.FS

// Test TODO
//
//go:embed *.sql
var Test embed.FS

// SQLScript TODO
//
//go:embed *.sql
var SQLScript embed.FS
