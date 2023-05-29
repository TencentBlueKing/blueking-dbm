package staticembed

import "embed"

// SysInitEsScriptFileName TODO
var SysInitEsScriptFileName = "sysinit_es.sh"

// SysInitEsScript TODO
//
//go:embed sysinit_es.sh
var SysInitEsScript embed.FS
