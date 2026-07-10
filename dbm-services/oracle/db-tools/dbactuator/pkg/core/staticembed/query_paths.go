package staticembed

import "embed"

// QueryPathsSQLFileName TODO
var QueryPathsSQLFileName = "query_paths.sql"

// QueryPathsSQL TODO
//
//go:embed query_paths.sql
var QueryPathsSQL embed.FS
