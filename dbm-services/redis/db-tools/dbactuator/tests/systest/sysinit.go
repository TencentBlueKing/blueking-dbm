// Package systest mysys test
package systest

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomsys"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"time"
)

// SysInitTest 系统初始化测试
type SysInitTest struct {
	atomsys.SysInitParams
	Err error `json:"-"`
}

// Run run
func (test *SysInitTest) Run() {
	msg := fmt.Sprintf("=========sys_init test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========sys_init test fail============")
		} else {
			msg = fmt.Sprintf("=========sys_init test success============")
		}
		fmt.Println(msg)
	}()
	test.User = consts.MysqlAaccount
	test.Password = "xxxx"
	paramBytes, _ := json.Marshal(test)
	initCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomsys.NewSysInit().Name(), string(paramBytes))
	fmt.Println(initCmd)
	_, test.Err = util.RunBashCmd(initCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// RunSysInit run sysinit
func RunSysInit() error {
	test := &SysInitTest{}
	test.Run()
	return test.Err
}
