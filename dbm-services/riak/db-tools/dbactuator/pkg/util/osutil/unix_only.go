//go:build !windows
// +build !windows

package osutil

import (
	"bytes"
	"fmt"
	"math/rand"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// IsMountPoint TODO
// Determine if a directory is a mountpoint, by comparing the device for the directory
// with the device for it's parent.  If they are the same, it's not a mountpoint, if they're
// different, it is.
// reference: https://github.com/cnaize/kubernetes/blob/master/pkg/util/mount/mountpoint_unix.go#L29
func IsMountPoint(file string) (bool, error) {
	stat, err := os.Stat(file)
	if err != nil {
		return false, err
	}
	rootStat, err := os.Lstat(file + "/..")
	if err != nil {
		return false, err
	}
	// If the directory has the same device as parent, then it's not a mountpoint.
	return stat.Sys().(*syscall.Stat_t).Dev != rootStat.Sys().(*syscall.Stat_t).Dev, nil
}

// FindFirstMountPoint find first mountpoint in prefer order
func FindFirstMountPoint(paths ...string) (string, error) {
	for _, path := range paths {
		if _, err := os.Stat(path); err != nil {
			if os.IsNotExist(err) {
				continue
			}
		}
		isMountPoint, err := IsMountPoint(path)
		if err != nil {
			return "", fmt.Errorf("check whether mountpoint failed, path: %s, err: %w", path, err)
		}
		if isMountPoint {
			return path, nil
		}
	}
	return "", fmt.Errorf("no available mountpoint found, choices: %#v", paths)
}

// RunShellCmdAsUser a simple wrapper of Cmd
// NOTE(wangqingping) len(strings.Join(args, " ")) cannot
// exceed MAX_ARG_STRLEN, checkout:
// https://www.linuxjournal.com/article/6060
func RunShellCmdAsUser(args []string, osuser string) (string, error) {
	cmd := exec.Command("bash", "-c", strings.Join(args, " "))
	var outbuff, errbuff bytes.Buffer
	cmd.Stdout = &outbuff
	cmd.Stderr = &errbuff
	uid, gid, err := GetUidGid(osuser)
	if err != nil {
		return "", err
	}
	cmd.SysProcAttr = &syscall.SysProcAttr{}
	cmd.SysProcAttr.Credential = &syscall.Credential{Uid: uint32(uid), Gid: uint32(gid)}
	if err := cmd.Run(); err != nil {
		logger.Info(
			"Run command failed, cmd `%s` error %s, %s",
			strings.Join(args, " "), errbuff.String(), err,
		)
		return "", err
	} else {
		logger.Info("Run command `%s` successfully", strings.Join(args, " "))
	}
	return outbuff.String(), nil
}

// RunShellCmdNoWaitAsUser TODO
// starts the specified command but does not wait for it to complete.
func RunShellCmdNoWaitAsUser(args []string, osuser string) (string, error) {
	cmd := exec.Command("bash", "-c", strings.Join(args, " "))
	var outbuff, errbuff bytes.Buffer
	cmd.Stdout = &outbuff
	cmd.Stderr = &errbuff
	uid, gid, err := GetUidGid(osuser)
	if err != nil {
		return "", err
	}
	cmd.SysProcAttr = &syscall.SysProcAttr{}
	cmd.SysProcAttr.Credential = &syscall.Credential{Uid: uint32(uid), Gid: uint32(gid)}
	if err := cmd.Start(); err != nil {
		logger.Info(
			"Run command failed, cmd `%s` error %s, %s",
			strings.Join(args, " "), errbuff.String(), err,
		)
		return "", err
	} else {
		logger.Info("Run command `%s` successfully", strings.Join(args, " "))
	}

	return outbuff.String(), nil
}

// Lock TODO
func (l *DirLock) Lock() error {
	f, err := os.Open(l.dir)
	if err != nil {
		return err
	}
	l.f = f
	err = syscall.Flock(int(l.f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB)
	if err != nil {
		return fmt.Errorf("cannot flock directory %s - %w", l.dir, err)
	}
	return nil
}

// Unlock TODO
func (l *DirLock) Unlock() error {
	defer func() {
		if err := l.f.Close(); err != nil {
			logger.Warn("close lock file failed, err:%s", err.Error())
		}
	}()
	return syscall.Flock(int(l.f.Fd()), syscall.LOCK_UN)
}

// GetDirLock TODO
/*
 GetDirLock 获取 crontab lock.
 set waitTime = 0 if you don't want to wait crontab lock
*/
func GetDirLock(waitTime time.Duration, l *DirLock) error {
	var (
		flockErr    = make(chan error, 1)
		timeoutChan = make(chan struct{})
		err         error
	)

	if waitTime == 0 {
		return l.Lock()
	}

	go func() {
		var deadline = time.Now().Add(waitTime)
		for {
			err := l.Lock()
			if err == nil {
				flockErr <- err
				return
			}
			logger.Error("get file lock error:%s,continue to wait", err)
			if time.Until(deadline) < 0 {
				timeoutChan <- struct{}{}
				return
			}
			time.Sleep(time.Duration(7+rand.Intn(7)) * time.Second)
		}
	}()

	select {
	case err := <-flockErr:
		return err
	case <-timeoutChan:
		err = fmt.Errorf("lock file(%s) timeout", l.GetDirName())
		return err
	}
}

// ReleaseDirLock TODO
func ReleaseDirLock(l *DirLock) error {
	return l.Unlock()
}

// DirLock TODO
// from https://github.com/nsqio/nsq/blob/master/internal/dirlock/dirlock.go
type DirLock struct {
	dir string
	f   *os.File
}

// NewDirLock TODO
func NewDirLock(dir string) *DirLock {
	isExist := FileExist(dir)
	if !isExist {
		_, err := os.OpenFile(dir, os.O_RDWR|os.O_CREATE, 0755)
		if err != nil {
			logger.Warn("openFile(%s) error:%s", dir, err)
		}
	}
	return &DirLock{
		dir: dir,
	}
}

// GetDirName TODO
func (l *DirLock) GetDirName() string {
	return l.dir
}
