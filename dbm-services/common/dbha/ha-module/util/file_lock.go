package util

import (
	"os"
	"syscall"

	"dbm-services/common/dbha/ha-module/log"
)

// FileLock file lock struct
type FileLock struct {
	Path string
	Fd   *os.File
}

// NewFileLock init file lock
func NewFileLock(path string) *FileLock {
	return &FileLock{
		Path: path,
	}
}

// Lock do lock
func (l *FileLock) Lock() error {
	f, err := os.OpenFile(l.Path, os.O_RDWR|os.O_CREATE, os.ModePerm)
	if err != nil {
		log.Logger.Errorf("FileLock open file failed,path:%s,err:%s",
			l.Path, err.Error())
		return err
	}

	l.Fd = f
	err = syscall.Flock(int(f.Fd()), syscall.LOCK_EX)
	if err != nil {
		log.Logger.Errorf("FileLock lock failed,path:%s,fd:%d,err:%s",
			l.Path, int(f.Fd()), err.Error())
		return err
	}

	return nil
}

// UnLock do unlock
func (l *FileLock) UnLock() error {
	if nil == l.Fd {
		log.Logger.Warnf("FileLock fd is nil")
		return nil
	}

	err := syscall.Flock(int(l.Fd.Fd()), syscall.LOCK_UN)
	if err != nil {
		log.Logger.Infof("FileLock unlock failed,path:%s,fd:%d,err:%s",
			l.Path, int(l.Fd.Fd()), err.Error())
		l.Fd.Close()
		return err
	} else {
		l.Fd.Close()
		return nil
	}
}
