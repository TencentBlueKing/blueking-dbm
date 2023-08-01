package config

import (
	"os"
	"path/filepath"
)

var BaseDir string

func init() {
	executable, _ := os.Executable()
	BaseDir = filepath.Dir(executable)
	_ = os.MkdirAll(filepath.Join(BaseDir, "collect"), 0755)
	_ = os.MkdirAll(filepath.Join(BaseDir, "logs"), 0755)
}
