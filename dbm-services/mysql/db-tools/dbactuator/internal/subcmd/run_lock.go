package subcmd

import (
	"fmt"
	"os"
	"path/filepath"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/gofrs/flock"
)

const runLockFileName = ".dbactuator.%s.%s.%s.lock"

var runLock *flock.Flock

func runLockFilePath(uid, rootID, nodeID string) (string, error) {
	executable, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("get executable path failed: %w", err)
	}
	return filepath.Join(filepath.Dir(executable), fmt.Sprintf(runLockFileName, uid, rootID, nodeID)), nil
}

func shouldUseRunLock(opt *BaseOptions) bool {
	return opt != nil && opt.Uid != "" && opt.RootId != "" && opt.NodeId != ""
}

// AcquireRunLock 基于 uid/root_id/node_id 做进程互斥，避免同一流程节点并发执行。
func AcquireRunLock(opt *BaseOptions) error {
	if !shouldUseRunLock(opt) {
		logger.Info("skip run lock: uid/root_id/node_id not all set")
		return nil
	}

	lockPath, err := runLockFilePath(opt.Uid, opt.RootId, opt.NodeId)
	if err != nil {
		return err
	}

	logger.Info("waiting run lock: %s", lockPath)
	runLock = flock.New(lockPath)
	if err := runLock.Lock(); err != nil {
		runLock = nil
		return fmt.Errorf("acquire run lock %s failed: %w", lockPath, err)
	}
	logger.Info("acquire run lock successfully: %s", lockPath)
	return nil
}

// ReleaseRunLock 释放 AcquireRunLock 获取的锁。
func ReleaseRunLock() {
	if runLock == nil {
		return
	}
	lockPath := runLock.Path()
	if err := runLock.Unlock(); err != nil {
		logger.Warn("release run lock %s failed: %s", lockPath, err.Error())
	} else {
		logger.Info("release run lock successfully: %s", lockPath)
	}
	runLock = nil
}
