// Package sysinit TODO
package sysinit

import (
	"fmt"
	"io/ioutil"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
)

// ExecSysInitScript TODO
func ExecSysInitScript() (err error) {
	data, err := staticembed.SysInitRiakScript.ReadFile(staticembed.SysInitRiakScriptFileName)
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
	_, err = osutil.StandardShellCommand(false, command)
	if err != nil {
		logger.Error("exec sysinit script failed %s", err.Error())
		return err
	}
	return nil
}

// InitExternal TODO
func InitExternal() (err error) {
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
