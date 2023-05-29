package staticembed

import "embed"

// SysInitMySQLScriptFileName TODO
var SysInitMySQLScriptFileName = "sysinit_mysql.sh"

// ExternalScriptFileName TODO
var ExternalScriptFileName = "external.sh"

// SysInitMySQLScript TODO
//
//go:embed sysinit_mysql.sh
var SysInitMySQLScript embed.FS

// ExternalScript TODO
//
//go:embed external.sh
var ExternalScript embed.FS
