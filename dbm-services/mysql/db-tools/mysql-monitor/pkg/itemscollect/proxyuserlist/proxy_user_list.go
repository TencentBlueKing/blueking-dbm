// Package proxyuserlist proxy用户列表
package proxyuserlist

import (
	"fmt"
	"log/slog"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
)

var name = "proxy-user-list"

// Checker TODO
type Checker struct {
	adminDB *sqlx.DB
	db      *sqlx.DB
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	err = c.cleanOldBackup()
	if err != nil {
		return "", err
	}

	usersFromMem, err := c.loadUsersFromMem()
	if err != nil {
		return "", err
	}

	err = c.backupToBackend(usersFromMem)
	if err != nil {
		return "", err
	}

	err = c.backupToBackend(usersFromMem)
	if err != nil {
		return "", err
	}

	usersFromFile, err := c.loadUsersFromFile()
	if err != nil {
		return "", err
	}

	onlyInMem, onlyInFile := c.compareMemAndFile(usersFromMem, usersFromFile)

	var msgs []string

	if len(onlyInFile) > 0 {
		msgs = append(msgs, fmt.Sprintf("user only in file: %s", strings.Join(onlyInFile, ",")))
	}
	if len(onlyInMem) > 0 {
		slog.Info("user only in memory", slog.String("users", strings.Join(onlyInMem, ",")))
		err := c.refreshUsersToFile(onlyInMem)
		if err != nil {
			msgs = append(msgs,
				fmt.Sprintf("refresh users [%v] failed: %s", onlyInMem, err.Error()))
		}
	}

	return strings.Join(msgs, "\n"), nil
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		adminDB: cc.ProxyAdminDB,
		db:      cc.ProxyDB,
	}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
