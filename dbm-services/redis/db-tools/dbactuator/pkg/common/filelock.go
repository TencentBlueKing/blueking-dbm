package common

import (
	"os"
	"syscall"
)

// FileLock 结构体
type FileLock struct {
	Path string
	FD   *os.File
}

// NewFileLock 生成结构体
func NewFileLock(path string) *FileLock {
	fd, _ := os.Open(path)
	return &FileLock{
		Path: path,
		FD:   fd,
	}
}

// Lock 加锁
func (f *FileLock) Lock() error {
	err := syscall.Flock(int(f.FD.Fd()), syscall.LOCK_EX|syscall.LOCK_NB)
	return err
}

// UnLock 解锁
func (f *FileLock) UnLock() error {
	defer f.FD.Close()
	err := syscall.Flock(int(f.FD.Fd()), syscall.LOCK_UN)
	return err
}
