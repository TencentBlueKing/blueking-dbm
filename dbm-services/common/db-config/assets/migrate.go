package assets

import (
	"embed"
)

// Migrations TODO
//
//go:embed migrations/*.sql
var Migrations embed.FS
