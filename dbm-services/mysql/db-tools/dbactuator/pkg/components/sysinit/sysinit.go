// Package sysinit TODO
package sysinit

import (
	"fmt"
	"io/ioutil"
	"os"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
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
	if err = os.WriteFile(tmpScriptName, data, 07555); err != nil {
		logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	command := fmt.Sprintf("/bin/bash -c \"%s\"", tmpScriptName)
	_, err = osutil.StandardShellCommand(false, command)
	if err != nil {
		logger.Error("exec sysinit script failed %s", err.Error())
		return err
	}
	return nil
}

// InitExternal TODO
func (s *SysInitParam) InitExternal() (err error) {
	data, err := staticembed.ExternalScript.ReadFile(staticembed.ExternalScriptFileName)
	if err != nil {
		logger.Error("read sysinit script failed %s", err.Error())
		return err
	}
	tmpScriptName := "/tmp/yum_install_perl_dep.sh"
	if err = ioutil.WriteFile(tmpScriptName, data, 07555); err != nil {
		logger.Error("write tmp script failed %s", err.Error())
		return err
	}
	command := fmt.Sprintf("/bin/bash -c \"%s\"", tmpScriptName)
	_, err = osutil.StandardShellCommand(false, command)
	if err != nil {
		logger.Error("yum install perl dep failed %s", err.Error())
		return err
	}
	return nil
}

// GetTimeZone 增加机器初始化后输出机器的时区配置
func (s *SysInitParam) GetTimeZone() (timeZone string, err error) {
	execCmd := "date +%:z"
	output, err := osutil.StandardShellCommand(false, execCmd)
	if err != nil {
		logger.Error("exec get date script failed %s", err.Error())
		return "", err
	}
	return osutil.CleanExecShellOutput(output), nil

}
