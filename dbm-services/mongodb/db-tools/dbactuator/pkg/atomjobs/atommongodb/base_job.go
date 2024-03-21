package atommongodb

import (
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
	"fmt"
	"os"
	"os/user"
	"path/filepath"

	"github.com/pkg/errors"
)

// BaseJob 基础任务
type BaseJob struct {
	runtime *jobruntime.JobGenericRuntime
	OsUser  string
}

// Param 获取原子任务的参数
func (job *BaseJob) Param() string {
	return "Not Implemented"
}

// Retry 重试 一般不实现
func (job *BaseJob) Retry() uint {
	// do nothing
	return 2
}

// Rollback 回滚 一般不实现
func (job *BaseJob) Rollback() error {
	return nil
}

// checkIsRootUser 检查当前用户是否为Root用户
func checkIsRootUser() bool {
	currentUser, err := user.Current()
	if err != nil {
		return false
	}
	return currentUser.Username == "root"
}

func (job *BaseJob) chdir(dstDir string) error {
	wd, err := os.Getwd()
	if err != nil {
		return errors.Wrap(err, "os.getwd")
	}
	if err = os.Chdir(dstDir); err != nil {
		return errors.Wrap(err, fmt.Sprintf("os.chdir from %s to %s", wd, dstDir))
	} else {
		job.runtime.Logger.Info("os.chdir from %s to %s", wd, dstDir)
	}
	return nil
}

type stepFunc struct {
	name string
	run  func() (err error)
}

// runSteps 按顺序执行步骤函数
func (job *BaseJob) runSteps(steps []stepFunc) error {
	for _, f := range steps {
		job.runtime.Logger.Info("run %s start", f.name)
		if err := f.run(); err != nil {
			job.runtime.Logger.Error("run %s failed. err %s", f.name, err.Error())
			return errors.Wrap(err, f.name)
		}
		job.runtime.Logger.Info("run %s done", f.name)
	}
	return nil
}

// removeAll 删除目录，且目录不能为根目录
func (job *BaseJob) removeDir(dstDir string) error {
	if dstDir == "" {
		return errors.New("invalid dstDir")
	}
	absPath, err := filepath.Abs(dstDir)
	if err != nil {
		return errors.Wrap(err, fmt.Sprintf("filepath.Abs %s", dstDir))
	}
	if absPath == "/" {
		return errors.New("invalid dstDir")
	}

	if err := os.RemoveAll(dstDir); err != nil {
		return errors.Wrap(err, fmt.Sprintf("removeDir %s", dstDir))
	} else {
		job.runtime.Logger.Info("removeDir %s absPath:%s", dstDir, absPath)
	}
	return nil
}
