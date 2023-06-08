package cmutil

import (
	"crypto/md5"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/pkg/errors"
)

// GetFileMd5 获取文件MD5
func GetFileMd5(fileAbPath string) (md5sum string, err error) {
	f, err := filepath.Abs(fileAbPath)
	if err != nil {
		return
	}
	rFile, err := os.Open(f)
	if err != nil {
		return "", err
	}
	defer rFile.Close()
	h := md5.New()
	if _, err := io.Copy(h, rFile); err != nil {
		return "", err
	}
	return fmt.Sprintf("%x", h.Sum(nil)), nil
}

// FileExists 检查目录是否已经存在
func FileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		return os.IsExist(err)
	}
	return true
}

// FileExistsErr 如果文件不存在则抛出 error
func FileExistsErr(path string) error {
	_, err := os.Stat(path)
	if err != nil {
		return errors.WithStack(err)
	}
	return nil
}

// IsDirectory 检查本机路径是否是目录
func IsDirectory(path string) bool {
	fileInfo, err := os.Stat(path)
	if err != nil {
		return false
	}
	return fileInfo.IsDir()
}

// GetFileSize get file size from os
func GetFileSize(path string) int64 {
	f, err := os.Stat(path)
	if err != nil {
		// 有可能没权限，有可能不存在
		if os.IsNotExist(err) {
			return -1
		} else if os.IsPermission(err) {
			return -2
		} else {
			return -3
		}
	}
	return f.Size()
}
