package cmutil

import (
	"crypto/md5"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

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

// IsSymLinkFile 文件是否是软连
func IsSymLinkFile(path string) (bool, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return false, err
	} else if info.Mode()&os.ModeSymlink > 0 { // 是软链
		return true, nil
	} else {
		return false, nil
	}
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

func GetFileModifyTime(filename string) (bool, int64) {
	if _, err := os.Stat(filename); !os.IsNotExist(err) {
		f, err1 := os.Open(filename)
		if err1 != nil {
			return true, 0
		}
		fi, err2 := f.Stat()
		if err2 != nil {
			return true, 0
		}
		return true, fi.ModTime().Unix()
	}
	return false, 0
}

// OSCopyFile os cp file
func OSCopyFile(srcFile, dstFile string) error {
	_, errStr, err := ExecCommand(true, "", "cp", "-p", srcFile, dstFile)
	if err != nil {
		return errors.New(errStr)
	}
	return nil
}

// SafeRmDir TODO
func SafeRmDir(dir string) (err error) {
	if strings.TrimSpace(dir) == "/" {
		return fmt.Errorf("禁止删除系统根目录")
	}
	return os.RemoveAll(dir)
}
