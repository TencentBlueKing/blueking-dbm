package config

import (
	"os"
	"path/filepath"
)

// CheckMode 校验模式
type CheckMode string

const (
	// GeneralMode 常规校验
	GeneralMode CheckMode = "general"
	// DemandMode 单据校验
	DemandMode         = "demand"
	ResultDb           = "infodba_schema"
	ResultTable        = "checksum"
	ResultHistoryTable = "checksum_history"
)

var Executable string
var ExecutableName string
var ExecutablePath string

// String 用于打印
func (c CheckMode) String() string {
	return string(c)
}

func init() {
	Executable, _ = os.Executable()
	ExecutableName = filepath.Base(Executable)
	ExecutablePath = filepath.Dir(Executable)
}
