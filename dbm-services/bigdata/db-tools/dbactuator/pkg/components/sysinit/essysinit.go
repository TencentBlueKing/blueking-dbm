package sysinit

import (
	"fmt"
	"io/ioutil"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
)

// EsSysInitParam TODO
// Todo
type EsSysInitParam struct {
}

// EsSysInitMachine TODO
/*
	执行系统初始化脚本，对应job的节点初始化脚本
	创建mysql账户等操作
*/
func (s *EsSysInitParam) EsSysInitMachine() error {
	logger.Info("start exec sysinit ...")
	return ExecEsSysInitScript()
}

// ExecEsSysInitScript TODO
// Todo
func ExecEsSysInitScript() (err error) {
	data, err := staticembed.SysInitEsScript.ReadFile(staticembed.SysInitEsScriptFileName)
	if err != nil {
		logger.Error("read es sysinit script failed %s", err.Error())
		return err
	}
	tmpScriptName := "/tmp/essysinit.sh"
	if err = ioutil.WriteFile(tmpScriptName, data, 07555); err != nil {
		logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	command := fmt.Sprintf("/bin/bash -c \"%s\"", tmpScriptName)
	_, err = osutil.ExecShellCommand(false, command)
	if err != nil {
		logger.Error("exec es sysinit script failed %s", err.Error())
		return err
	}
	return nil
}
