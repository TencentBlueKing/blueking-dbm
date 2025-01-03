package proxyuserlist

import (
	"bufio"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
)

func (c *Checker) loadUsersFromMem() ([]string, error) {
	var usersFromQuery []string
	err := c.adminDB.Select(&usersFromQuery, `SELECT * FROM USERS`)
	if err != nil {
		slog.Error("query user list", slog.String("error", err.Error()))
		return nil, err
	}

	return usersFromQuery, nil
}

func (c *Checker) loadUsersFromFile() ([]string, error) {
	userListFilePath := filepath.Join(
		"/etc",
		fmt.Sprintf(`proxy_user.cnf.%d`, config.MonitorConfig.Port),
	)
	f, err := os.Open(userListFilePath)
	if err != nil {
		slog.Error("read proxy user list file", slog.String("error", err.Error()))
		return nil, err
	}
	defer func() {
		_ = f.Close()
	}()

	var usersFromFile []string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		usersFromFile = append(usersFromFile, scanner.Text())
		err := scanner.Err()
		if err != nil {
			slog.Error("scan proxy user list file", slog.String("error", err.Error()))
			return nil, err
		}
	}

	return usersFromFile, nil
}
