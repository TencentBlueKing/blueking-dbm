package cmd

import (
	"os"
)

var executable string

func init() {
	executable, _ = os.Executable()
}
