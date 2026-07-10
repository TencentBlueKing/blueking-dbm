package staticembed

import "embed"

// TnsNamesFileName TODO
var TnsNamesFileName = "tnsnames.ora"

// TnsNames TODO
//
//go:embed tnsnames.ora
var TnsNames embed.FS
