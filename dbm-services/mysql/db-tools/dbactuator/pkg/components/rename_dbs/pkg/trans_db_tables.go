package pkg

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
)

func TransDBTables(conn *sqlx.Conn, from, to string, tables []string) error {
	for _, table := range tables {
		err := transDBTable(conn, from, to, table)
		if err != nil {
			return err
		}
	}
	return nil
}

func transDBTable(conn *sqlx.Conn, from, to, tableName string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// 这里的表是 backup others 新建出来的
	_, err := conn.ExecContext(
		ctx,
		fmt.Sprintf("DROP TABLE IF EXISTS `%s`.`%s`;", to, tableName),
	)
	if err != nil {
		return err
	}

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf(
			"RENAME TABLE `%s`.`%s` TO `%s`.`%s`",
			from, tableName, to, tableName,
		),
	)
	if err != nil {
		logger.Info("rename %s from %s to %s failed: %s", tableName, from, to, err.Error())
		return err
	}
	logger.Info("rename %s from %s to %s success", tableName, from, to)
	return nil
}
