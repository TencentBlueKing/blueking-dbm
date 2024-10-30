package consts

import (
	"os"
)

// fileExists 检查目录是否已经存在
func fileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}
