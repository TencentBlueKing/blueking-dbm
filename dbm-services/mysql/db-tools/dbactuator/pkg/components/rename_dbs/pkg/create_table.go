package pkg

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
)

func CreateTablesLike(conn *sqlx.Conn, sourceDBName, destDBName string, tables []string) error {
	for _, table := range tables {
		err := CreateTableLike(conn, sourceDBName, destDBName, table)
		if err != nil {
			logger.Error("create table %s failed: %s", table, err)
			return err
		}
		logger.Info("create table %s success", table)
	}
	return nil
}

func CreateTableLike(conn *sqlx.Conn, sourceDBName, destDBName, tableName string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var _tb, createTableStr string
	err := conn.QueryRowxContext(
		ctx,
		fmt.Sprintf("SHOW CREATE TABLE `%s`.`%s`", sourceDBName, tableName),
	).Scan(&_tb, &createTableStr)
	if err != nil {
		logger.Error("show create table %s failed: %s", tableName, err)
		return err
	}
	logger.Info("show create table %s success: %s", tableName, createTableStr)

	_, err = conn.ExecContext(ctx, fmt.Sprintf("USE `%s`", destDBName))
	if err != nil {
		logger.Error("use db %s failed: %s", destDBName, err)
		return err
	}
	logger.Info("use db %s success", destDBName)

	_, err = conn.ExecContext(ctx, createTableStr)
	if err != nil {
		logger.Error("create table %s failed: %s", tableName, err)
		return err
	}
	logger.Info("create table %s success", tableName)
	return nil
}
