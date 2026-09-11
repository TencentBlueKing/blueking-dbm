package staticembed

import "embed"

// RMANDuplicateSlowlyScriptFileName TODO
var RMANDuplicateSlowlyScriptFileName = "rman_duplicate_slowly.sh"

// RMANDuplicateSlowlyScript TODO
//
//go:embed rman_duplicate_slowly.sh
var RMANDuplicateSlowlyScript embed.FS
