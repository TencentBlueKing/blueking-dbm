package proxyuserlist

import (
	"context"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"
)

func (c *Checker) backupToBackend(users []string) error {
	now := time.Now()
	conn, err := c.db.Connx(context.Background())
	if err != nil {
		return err
	}
	defer func() {
		_ = conn.Close()
	}()

	_, err = conn.ExecContext(context.Background(), `SET SESSION binlog_format='statement';`)
	if err != nil {
		return err
	}

	stmt, err := conn.PreparexContext(
		context.Background(),
		`REPLACE INTO infodba_schema.proxy_user_list 
        			(proxy_ip, username, host, create_at) VALUES (?, ?, ?, ?)`,
	)
	if err != nil {
		slog.Error("backup proxy user list prepare", slog.String("err", err.Error()))
		return err
	}
	defer func() {
		_ = stmt.Close()
	}()

	for _, user := range users {
		splitUser := strings.Split(user, "@")
		if len(splitUser) != 2 {
			err := fmt.Errorf("invalid user %s", user)
			slog.Error("backup proxy user list prepare", slog.String("err", err.Error()))
			return err
		}
		username := splitUser[0]
		host := splitUser[1]

		err := writeOne(stmt, username, host, now)

		if err != nil {
			return err
		}
	}
	return nil
}

func writeOne(stmt *sqlx.Stmt, username, host string, now time.Time) error {
	_, err := stmt.Exec(
		config.MonitorConfig.Ip,
		username,
		host,
		now,
	)
	if err != nil {
		slog.Error("backup proxy user list exec", slog.String("err", err.Error()))
		return err
	}
	return nil
}

func (c *Checker) cleanOldBackup() error {
	conn, err := c.db.Connx(context.Background())
	if err != nil {
		return err
	}
	defer func() {
		_ = conn.Close()
	}()

	_, err = conn.ExecContext(context.Background(), `SET SESSION binlog_format='statement';`)
	if err != nil {
		return err
	}

	_, err = conn.ExecContext(
		context.Background(),
		`DELETE FROM infodba_schema.proxy_user_list 
       				WHERE create_at < DATE(NOW() - INTERVAL 7 DAY)`,
	)
	if err != nil {
		slog.Error("backup proxy user list delete", slog.String("err", err.Error()))
		return err
	}
	return nil
}
