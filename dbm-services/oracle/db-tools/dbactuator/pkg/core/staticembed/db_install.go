package staticembed

import "embed"

// DBInstallRSPFileName TODO
var DBInstallRSPFileName = "db_install.rsp"

// DBInstallRSP TODO
//
//go:embed db_install.rsp
var DBInstallRSP embed.FS
