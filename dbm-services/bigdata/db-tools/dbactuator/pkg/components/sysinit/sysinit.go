// Package sysinit TODO
package sysinit

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"io/ioutil"
)

// SysInitParam TODO
type SysInitParam struct {
	OsMysqlUser string `json:"user"`
	OsMysqlPwd  string `json:"pwd"`
}

/*
	执行系统初始化脚本 原来的sysinit.sh
	创建mysql账户等操作
*/

// SysInitMachine TODO
func (s *SysInitParam) SysInitMachine() error {
	logger.Info("start exec sysinit ...")
	return ExecSysInitScript()
}

// SetOsPassWordForMysql TODO
func (s *SysInitParam) SetOsPassWordForMysql() error {
	logger.Info("start set os pwd ...")
	return osutil.SetOSUserPassword(s.OsMysqlUser, s.OsMysqlPwd)
}

// ExecSysInitScript TODO
func ExecSysInitScript() (err error) {
	data, err := staticembed.SysInitMySQLScript.ReadFile(staticembed.SysInitMySQLScriptFileName)
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
