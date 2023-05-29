package staticembed

import "embed"

// SysInitHdfsScriptFileName TODO
var SysInitHdfsScriptFileName = "sysinit_hdfs.sh"

// SysInitHdfsScript TODO
//
//go:embed sysinit_hdfs.sh
var SysInitHdfsScript embed.FS
