// Package main TODO
/*
Copyright © 2022 NAME HERE <EMAIL ADDRESS>

*/
package main

import (
	"dbm-services/mongodb/db-tools/dbmon/cmd"
	"runtime"
)

// parselog 需要较多cpu
func init() {
	cpuNum := runtime.NumCPU()
	if cpuNum >= 16 {
		runtime.GOMAXPROCS(cpuNum / 8)
	} else {
		runtime.GOMAXPROCS(1)
	}
}

func main() {
	cmd.Execute()
}
