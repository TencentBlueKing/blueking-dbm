package pkg

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
)

type createTriggerRow struct {
	Trigger             string `db:"Trigger"`
	SqlMode             string `db:"sql_mode"`
	Sql                 string `db:"SQL Original Statement"`
	CharsetClient       string `db:"character_set_client"`
	CollationConnection string `db:"collation_connection"`
	Collation           string `db:"Database Collation"`
	Created             string `db:"Created"`
}

// TransDBTables
// 一个表如果有触发器, 必须要 drop 触发器才能 drop/rename
// 如果是 rename db 单据, 源触发器可以不用保留
// 如果是 truncate db, 当清档类型是 truncate table 时, 源触发器需要保留
// 实际是 rename table 前先把触发器删掉, 完事了再看需求重建
// 但是又不能在这个函数重建, 因为表还不在, 所以只能把需求重建的 trigger 返回
func TransDBTables(conn *sqlx.Conn, from, to string, tables []string) ([]string, error) {
	var res []string
	for _, table := range tables {
		createTriggers, err := transDBTable(conn, from, to, table)
		if err != nil {
			return nil, err
		}
		res = append(res, createTriggers...)
	}
	return res, nil
}

func flushTable(conn *sqlx.Conn, from, to, tableName string) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	_, err := conn.ExecContext(
		ctx,
		fmt.Sprintf("FLUSH TABLE `%s`.`%s`", from, tableName),
	)
	if err != nil {
		logger.Error("flushing table `%s`.`%s` failed: %s", from, tableName, err.Error())
	}

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf("FLUSH TABLE `%s`.`%s`", to, tableName),
	)
	if err != nil {
		logger.Error("flushing table `%s`.`%s` failed: %s", to, tableName, err.Error())
	}
}

func transDBTable(conn *sqlx.Conn, from, to, tableName string) ([]string, error) {
	defer func() {
		flushTable(conn, from, to, tableName)
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err := conn.ExecContext(
		ctx,
		`SET FOREIGN_KEY_CHECKS=0`,
	)
	if err != nil {
		return nil, err
	}

	// 这里的表是 backup others 新建出来的
	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf("DROP TABLE IF EXISTS `%s`.`%s`;", to, tableName),
	)
	if err != nil {
		return nil, err
	}

	// 源触发器
	var triggers []string
	err = conn.SelectContext(
		ctx,
		&triggers,
		`SELECT TRIGGER_NAME FROM INFORMATION_SCHEMA.TRIGGERS WHERE EVENT_OBJECT_SCHEMA = ? AND EVENT_OBJECT_TABLE = ?`,
		from, tableName,
	)
	if err != nil {
		logger.Error("query trigger for %s.%s failed: %s", from, tableName, err)
		return nil, err
	}
	logger.Info("query trigger for %s.%s succeeded: %v", from, tableName, triggers)

	var createTriggers []string
	for _, trigger := range triggers {
		createTrigger := createTriggerRow{}
		err = conn.GetContext(ctx, &createTrigger, fmt.Sprintf("SHOW CREATE TRIGGER `%s`.`%s`", from, trigger))
		if err != nil {
			logger.Error("show create trigger for %s.%s failed: %s", from, trigger, err)
			return nil, err
		}
		createTriggers = append(createTriggers, createTrigger.Sql)
		logger.Info("stage create trigger for %s.%s: %s", from, trigger, createTrigger.Sql)

		_, err = conn.ExecContext(ctx, fmt.Sprintf("DROP TRIGGER `%s`.`%s`", from, trigger))
		if err != nil {
			logger.Error("drop trigger for %s.%s failed: %s", from, trigger, err)
			return nil, err
		}
		logger.Info("drop trigger for %s.%s succeeded", from, trigger)
	}

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf(
			"RENAME TABLE `%s`.`%s` TO `%s`.`%s`",
			from, tableName, to, tableName,
		),
	)
	if err != nil {
		logger.Error("rename %s from %s to %s failed: %s", tableName, from, to, err.Error())
		return nil, err
	}
	logger.Info("rename %s from %s to %s success", tableName, from, to)
	return createTriggers, nil
}
