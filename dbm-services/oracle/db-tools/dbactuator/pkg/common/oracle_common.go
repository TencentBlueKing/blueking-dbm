package common

import (
	"fmt"
	"os"
	"time"

	"dbm-services/oracle/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/oracle/db-tools/dbactuator/pkg/util"
)

// CreateFileAndChown 创建Auth配置文件并修改属主
func CreateFileAndChown(runtime *jobruntime.JobGenericRuntime, filePath string,
	fileContent []byte, user string, group string, defaultPerm os.FileMode) error {
	runtime.Logger.Info("start to create %s file", filePath)
	file, err := os.OpenFile(filePath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, defaultPerm)
	defer file.Close()
	if err != nil {
		runtime.Logger.Error("create %s file fail, error:%s", filePath, err)
		return fmt.Errorf("create %s file fail, error:%s", filePath, err)
	}
	if _, err = file.WriteString(string(fileContent)); err != nil {
		runtime.Logger.Error("%s file write content fail, error:%s", filePath, err)
		return fmt.Errorf("%s file write content  fail, error:%s", filePath, err)
	}
	runtime.Logger.Info("create %s file successfully", filePath)

	// 修改配置文件属主
	runtime.Logger.Info("start to execute chown command for %s file", filePath)
	if _, err = util.RunBashCmd(
		fmt.Sprintf("chown -R %s.%s %s", user, group, filePath),
		"", nil,
		60*time.Second); err != nil {
		runtime.Logger.Error("chown %s file fail, error:%s", filePath, err)
		return fmt.Errorf("chown %s file fail, error:%s", filePath, err)
	}
	runtime.Logger.Info("execute chown command for %s file successfully", filePath)
	return nil
}
