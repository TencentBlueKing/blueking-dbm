package staticembed

import "embed"

// SysInitRiakScriptFileName TODO
var SysInitRiakScriptFileName = "sysinit_riak.sh"

// ExternalScriptFileName TODO
var ExternalScriptFileName = "external.sh"

// RiakConfigTemplateFileName TODO
var RiakConfigTemplateFileName = "riak.conf"

// SysInitMySQLScript TODO
//
//go:embed sysinit_riak.sh
var SysInitRiakScript embed.FS

// ExternalScript TODO
//
//go:embed external.sh
var ExternalScript embed.FS

// RiakConfigTemplate TODO
//
//go:embed riak.conf
var RiakConfigTemplate embed.FS
