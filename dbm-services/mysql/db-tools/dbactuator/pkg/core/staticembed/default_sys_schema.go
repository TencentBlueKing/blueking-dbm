package staticembed

import "embed"

// DefaultSysSchemaSQLFileName TODO
const DefaultSysSchemaSQLFileName = "default_sys_schema.sql"

// DefaultSysSchemaSQL TODO
//
//go:embed default_sys_schema.sql
var DefaultSysSchemaSQL embed.FS
