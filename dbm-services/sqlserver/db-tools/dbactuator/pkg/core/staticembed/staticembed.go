// Package staticembed TODO
package staticembed

import "embed"

const (
	// SysInitScriptFileName TODO
	SysInitScriptFileName = "sysinit.ps1"
	// InitSqlServerFileName TODO
	InitSqlServerFileName = "init_sqlserver.ps1"
	// TestFileName TODO
	TestFileName = "test.sql"
	// InitDBMMonitorFileName TODO
	InitDBMMonitorFileName = "monitor_dbm.sql"
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
