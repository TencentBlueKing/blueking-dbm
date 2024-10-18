package proxyuserlist

import (
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func (c *Checker) refreshUsersToFile(userList []string) error {
	userFilePath := filepath.Join(
		"/etc",
		fmt.Sprintf(`proxy_user.cnf.%d`, config.MonitorConfig.Port),
	)

	f, err := os.OpenFile(userFilePath, os.O_RDWR|os.O_APPEND, 0777)
	if err != nil {
		return err
	}
	defer func() {
		_ = f.Close()
	}()

	var realMissingUserList []string
	for _, u := range userList {
		if !isInUserFile(u, f) {
			realMissingUserList = append(realMissingUserList, u)
		}
	}

	_, err = f.WriteString(strings.Join(realMissingUserList, "\n"))
	return err
}
