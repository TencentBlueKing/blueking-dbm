package util

import (
	"errors"
	"os"
	"syscall"
)

// FileLock 文件锁工具方法实现
type FileLock struct {
	LockFileName string
	lock         *os.File
}

// NewFileLock 初始化文件锁对象
func NewFileLock(filename string) *FileLock {
	return &FileLock{LockFileName: filename}
}

// TryFileLock 尝试获取文件锁
func (f *FileLock) TryFileLock() error {
	var err error
	if f.LockFileName == "" {
		return errors.New("lock file is empty")
	}

	f.lock, err = os.Create(f.LockFileName)
	if err != nil {
		return err
	}

	// 上锁
	return syscall.Flock(int(f.lock.Fd()), syscall.LOCK_EX|syscall.LOCK_NB)
}

// ReleaseFileLock 释放文件锁
func (f *FileLock) ReleaseFileLock() {
	// 解锁
	if f.lock != nil {
		syscall.Flock(int(f.lock.Fd()), syscall.LOCK_UN)
	}

	// 删除文件
	if f.lock != nil {
		f.lock.Close()
		os.Remove(f.LockFileName)
	}
}
