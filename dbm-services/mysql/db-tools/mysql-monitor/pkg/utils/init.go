package utils

import (
	"os"
	"path/filepath"
)

var executable string
var executableName string
var executableDir string

func init() {
	executable, _ = os.Executable()
	executableName = filepath.Base(executable)
	executableDir = filepath.Dir(executable)
}
