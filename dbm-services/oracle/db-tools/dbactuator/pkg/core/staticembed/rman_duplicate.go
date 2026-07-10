package staticembed

import "embed"

// RMANDuplicateScriptFileName TODO
var RMANDuplicateScriptFileName = "rman_duplicate.sh"

// RMANDuplicateScript TODO
//
//go:embed rman_duplicate.sh
var RMANDuplicateScript embed.FS
