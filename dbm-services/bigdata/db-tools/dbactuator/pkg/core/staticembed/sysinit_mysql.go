package staticembed

import "embed"

// SysInitMySQLScriptFileName TODO
var SysInitMySQLScriptFileName = "sysinit_mysql.sh"

// SysInitMySQLScript TODO
//
//go:embed sysinit_mysql.sh
var SysInitMySQLScript embed.FS
