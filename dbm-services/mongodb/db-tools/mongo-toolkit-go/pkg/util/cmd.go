package util

import (
	"fmt"
	"os"
)

// GetFileSize 获取文件大小(单位byte)
func GetFileSize(filename string) (size int64, err error) {
	fileInfo, err := os.Stat(filename)
	if err != nil {
		err = fmt.Errorf("file:%s os.Stat fail,err:%v", filename, err)
		return
	}
	return fileInfo.Size(), nil
}

// HumanSize 人类可读的文件大小
func HumanSize(size int64) string {
	if size < 1024 {
		return fmt.Sprintf("%dB", size)
	} else if size < 1024*1024 {
		return fmt.Sprintf("%dKB", size/1024)
	} else if size < 1024*1024*1024 {
		return fmt.Sprintf("%dMB", size/1024/1024)
	} else {
		return fmt.Sprintf("%dGB", size/1024/1024/1024)
	}
}

// FileExists 检查目录是否已经存在
func FileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}
