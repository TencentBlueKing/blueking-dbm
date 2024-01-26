package atommongodb

import (
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
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
func (s *BaseJob) Param() string {
	return "Not Implemented"
}

func checkIsRootUser() bool {
	currentUser, err := user.Current()
	if err != nil {
		return false
	}
	return currentUser.Username == "root"
}

func (s *BaseJob) chdir(dstDir string) error {
	wd, err := os.Getwd()
	if err != nil {
		return errors.Wrap(err, "os.getwd")
	}
	if err = os.Chdir(dstDir); err != nil {
		return errors.Wrap(err, fmt.Sprintf("os.chdir from %s to %s", wd, dstDir))
	} else {
		s.runtime.Logger.Info("os.chdir from %s to %s", wd, dstDir)
	}
	return nil
}

// removeAll 删除目录
func (s *BaseJob) removeDir(dstDir string) error {
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
		s.runtime.Logger.Info("removeDir %s absPath:%s", dstDir, absPath)
	}
	return nil
}
