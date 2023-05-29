// Package proxy_backend TODO
package proxy_backend

import (
	"bufio"
	"context"
	"database/sql"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

var name = "proxy-backend"

// Checker TODO
type Checker struct {
	db *sqlx.DB
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	cnfPath := filepath.Join("/etc", fmt.Sprintf(`proxy.cnf.%d`, config.MonitorConfig.Port))
	f, err := os.Open(cnfPath)
	if err != nil {
		slog.Error("open proxy cnf file", err)
		return "", err
	}
	defer func() {
		_ = f.Close()
	}()

	var backendLine string
	pattern := regexp.MustCompile(`^proxy-backend-addresses.*`)
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		if err := scanner.Err(); err != nil {
			slog.Error("scan proxy cnf file", err)
			return "", err
		}

		if pattern.MatchString(line) {
			backendLine = strings.TrimSpace(line)
			break
		}
	}

	if backendLine == "" {
		err := errors.Errorf("proxy-backend-addresses not found in cnf")
		slog.Error("find backend in cnf", err)
		return "", nil
	}

	splitPattern := regexp.MustCompile(`\s*=\s*`)
	splitLine := splitPattern.Split(backendLine, -1)
	if len(splitLine) != 2 {
		err := errors.Errorf("invalid config: %s", backendLine)
		slog.Error("split proxy-backend-addresses", err)
		return "", nil
	}

	backendAddr := splitLine[1]

	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	var backendInfo struct {
		Ndx         sql.NullInt32  `db:"backend_ndx"`
		Address     sql.NullString `db:"address"`
		Stat        sql.NullString `db:"state"`
		Type        sql.NullString `db:"type"`
		Uuid        sql.NullString `db:"uuid"`
		ClientCount sql.NullInt32  `db:"connected_clients"`
	}
	err = c.db.QueryRowxContext(ctx, `SELECT * FROM BACKENDS`).StructScan(&backendInfo)
	if err != nil {
		slog.Error("query backends", err)
		return "", err
	}

	if backendAddr == "" || !backendInfo.Address.Valid || backendAddr != backendInfo.Address.String {
		msg = fmt.Sprintf("cnf.backend=%s, mem.backend=%s", backendAddr, backendInfo.Address.String)
	}

	return msg, nil
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{db: cc.ProxyAdminDB}
}

// Register TODO
func Register() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return name, New
}
