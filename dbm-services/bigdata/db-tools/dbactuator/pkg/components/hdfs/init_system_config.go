package hdfs

import (
	"fmt"
	"io/ioutil"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InitSystemConfigParams TODO
type InitSystemConfigParams struct {
	InstallConfig `json:"install"`
	HostMap       map[string]string `json:"host_map"`
}

// InitSystemConfigService TODO
type InitSystemConfigService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params *InitSystemConfigParams

	RollBackContext rollback.RollBackObjects
}

// InitSystemConfig TODO
func (i *InitSystemConfigService) InitSystemConfig() (err error) {

	for k, v := range i.Params.HostMap {
		deleteCommand := fmt.Sprintf("sed -i '/%s$/d' /etc/hosts", v)
		if _, err := osutil.ExecShellCommand(false, deleteCommand); err != nil {
			logger.Error("exec delete hostname failed %s", err.Error())
		}
		echoCommand := fmt.Sprintf("echo \"%s %s\" >> /etc/hosts", k, v)
		_, err = osutil.ExecShellCommand(false, echoCommand)
		if err != nil {
			logger.Error("exec update host failed %s", err.Error())
		}
	}
	data, err := staticembed.SysInitHdfsScript.ReadFile(staticembed.SysInitHdfsScriptFileName)
	if err != nil {
		logger.Error("read sysinit script failed %s", err.Error())
		return err
	}
	tmpScriptName := "/tmp/sysinit.sh"
	if err = ioutil.WriteFile(tmpScriptName, data, 07555); err != nil {
		logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	command := fmt.Sprintf("/bin/bash -c \"%s\"", tmpScriptName)
	_, err = osutil.ExecShellCommand(false, command)
	if err != nil {
		logger.Error("exec sysinit script failed %s", err.Error())
		return err
	}
	return nil
}
