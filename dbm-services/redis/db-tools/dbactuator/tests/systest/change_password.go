package systest

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomsys"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// ChangePasswordTest  redis清档
type ChangePasswordTest struct {
	atomsys.ChangePwdParams
	Err error `json:"-"`
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *ChangePasswordTest) SetIP(ip string) *ChangePasswordTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.IP = ip
	return test
}

// SetRole 设置实例角色
func (test *ChangePasswordTest) SetRole(role string) *ChangePasswordTest {
	if test.Err != nil {
		return test
	}
	test.Role = role
	return test
}

// SetParams Set Params
func (test *ChangePasswordTest) SetParams(ports []int, oldPwd, newPwd string) *ChangePasswordTest {
	if test.Err != nil {
		return test
	}
	for i := 0; i < len(ports); i++ {
		test.InsParam = append(
			test.InsParam,
			atomsys.InsParam{Port: ports[i], OldPassword: oldPwd, NewPassword: newPwd},
		)
	}
	return test
}

// RunChangePassword flush data
func (test *ChangePasswordTest) RunChangePassword() {
	msg := fmt.Sprintf("=========RunChangePassword start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RunChangePassword fail============")
		} else {
			msg = fmt.Sprintf("=========RunChangePassword success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomsys.NewChangePassword().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// ChangePassword 修改密码
func ChangePassword(serverIP, role, oldPwd, newPwd string, ports []int) (err error) {
	changePwdTest := ChangePasswordTest{}
	changePwdTest.SetIP(serverIP).SetRole(role).SetParams(ports, oldPwd, newPwd)
	if changePwdTest.Err != nil {
		return
	}

	changePwdTest.RunChangePassword()
	return changePwdTest.Err
}
