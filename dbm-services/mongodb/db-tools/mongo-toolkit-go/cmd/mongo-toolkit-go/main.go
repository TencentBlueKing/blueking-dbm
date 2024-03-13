// mongo-toolkit-go is a toolkit for mongodb
package main

import (
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/cmd/mongo-toolkit-go/tools"
)

var (
	VERSION    = "<>" // VERSION 由编译脚本注入
	BuildDate  = "<>" // BuildDate 由编译脚本注入
	CommitSha1 = "<>" // CommitSha1 由编译脚本注入
	GoVersion  = "<>" // GoVersion 由编译脚本注入
)

// main
func main() {
	tools.Execute(VERSION, BuildDate, CommitSha1, GoVersion)
}
