package atommongodb

import (
	"dbm-services/mongo/db-tools/dbactuator/pkg/jobruntime"
	"os/user"
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
