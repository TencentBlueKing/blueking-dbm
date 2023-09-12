package config

import (
	"os"
	"path/filepath"
)

var Executable string
var BaseDir string
var LogDir string
var CollectDir string

func init() {
	executable, _ := os.Executable()

	Executable = filepath.Base(executable)
	BaseDir = filepath.Dir(executable)
	LogDir = filepath.Join(BaseDir, "logs")
	CollectDir = filepath.Join(BaseDir, "collect")

	_ = os.MkdirAll(CollectDir, 0755)
	_ = os.MkdirAll(LogDir, 0755)
}
