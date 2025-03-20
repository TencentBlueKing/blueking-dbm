package consts

import (
	"fmt"
	"os"
	"os/exec"
)

// SetProcessUser 设置os用户
func SetProcessUser(user string) error {
	// 如果有user参数，设置环境变量
	if user != "" {
		envUser := os.Getenv("PROCESS_EXEC_USER")
		if envUser == user {
			return nil
		}
		envUser = user
		var ret []byte
		shCmd := fmt.Sprintf(`
ret=$(grep '^export PROCESS_EXEC_USER=' /etc/profile)
if [[ -z $ret ]]
then
echo "export PROCESS_EXEC_USER=%s">>/etc/profile
fi
	`, envUser)
		ret, err := exec.Command("bash", "-c", shCmd).Output()
		if err != nil {
			err = fmt.Errorf("SetProcessUser failed,err:%v,ret:%s", err, string(ret))
			return err
		}
		os.Setenv("PROCESS_EXEC_USER", envUser)
	}
	return nil
}

// GetProcessUser 获取os用户
func GetProcessUser() string {
	envUser := os.Getenv("PROCESS_EXEC_USER")
	if envUser == "" {
		return OSAccount
	}
	return envUser
}

// SetProcessUserGroup 设置os用户Group
func SetProcessUserGroup(group string) error {
	// 如果有user参数，设置环境变量
	if group != "" {
		envGroup := os.Getenv("PROCESS_EXEC_USER_GROUP")
		if envGroup == group {
			return nil
		}
		envGroup = group
		var ret []byte
		shCmd := fmt.Sprintf(`
ret=$(grep '^export PROCESS_EXEC_USER_GROUP=' /etc/profile)
if [[ -z $ret ]]
then
echo "export PROCESS_EXEC_USER_GROUP=%s">>/etc/profile
fi
	`, envGroup)
		ret, err := exec.Command("bash", "-c", shCmd).Output()
		if err != nil {
			err = fmt.Errorf("SetProcessUserGroup failed,err:%v,ret:%s", err, string(ret))
			return err
		}
		os.Setenv("PROCESS_EXEC_USER_GROUP", envGroup)

	}
	return nil
}

// GetProcessUserGroup 获取os用户group
func GetProcessUserGroup() string {
	envGroup := os.Getenv("PROCESS_EXEC_USER_GROUP")
	if envGroup == "" {
		return OSGroup
	}
	return envGroup
}
