package staticembed

import "embed"

// SysInitOracleScriptFileName TODO
var SysInitOracleScriptFileName = "sysinit_oracle.sh"

// SysInitOracleScript TODO
//
//go:embed sysinit_oracle.sh
var SysInitOracleScript embed.FS
