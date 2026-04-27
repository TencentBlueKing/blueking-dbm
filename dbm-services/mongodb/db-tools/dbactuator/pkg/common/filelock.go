package common

import (
	"fmt"
	"os"
	"syscall"
)

// FileLock 结构体
type FileLock struct {
	Path string
	FD   *os.File
}

// NewFileLock 生成结构体
func NewFileLock(path string) (*FileLock, error) {
	fd, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		return nil, err
	}
	return &FileLock{
		Path: path,
		FD:   fd,
	}, nil
}

// Lock 加锁
func (f *FileLock) Lock() error {
	if f == nil {
		return fmt.Errorf("file lock is nil")
	}
	if f.FD == nil {
		return fmt.Errorf("file lock fd is nil, lock path:%s", f.Path)
	}
	return syscall.Flock(int(f.FD.Fd()), syscall.LOCK_EX|syscall.LOCK_NB)
}

// UnLock 解锁
func (f *FileLock) UnLock() error {
	if f == nil || f.FD == nil {
		return nil
	}
	defer f.FD.Close()
	return syscall.Flock(int(f.FD.Fd()), syscall.LOCK_UN)
}
