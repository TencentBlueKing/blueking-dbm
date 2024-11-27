// Package fileutil 公共函数
package fileutil

import (
	"fmt"
	"os"
)

// FileExists 检查目录是否已经存在
func FileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}

// MkDirsIfNotExists 如果目录不存在则创建
func MkDirsIfNotExists(dirs []string) error {
	return MkDirsIfNotExistsWithPerm(dirs, 0755)
}

// MkDirsIfNotExistsWithPerm 如果目录不存在则创建，并指定文件Perm
func MkDirsIfNotExistsWithPerm(dirs []string, perm os.FileMode) error {
	for _, dir := range dirs {
		_, err := os.Stat(dir)
		if err == nil {
			continue
		}
		if os.IsNotExist(err) == true {
			err = os.MkdirAll(dir, perm)
			if err != nil {
				return fmt.Errorf("MkdirAll fail,err:%v,dir:%s", err, dirs)
			}
		}
	}
	return nil
}

// GetFileSize 获取文件大小(单位byte)
func GetFileSize(filename string) (size int64, err error) {
	fileInfo, err := os.Stat(filename)
	if err != nil {
		err = fmt.Errorf("file:%s os.Stat fail,err:%v", filename, err)
		return
	}
	return fileInfo.Size(), nil
}
