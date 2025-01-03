package pkg

import (
	"context"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs/pkg"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
)

func SafeDropSourceTables(conn *sqlx.Conn, dbName, stageDBName string, tables []string) error {
	for _, table := range tables {
		err := safeDropSourceTable(conn, dbName, stageDBName, table)
		if err != nil {
			return err
		}
	}
	return nil
}

func safeDropSourceTable(conn *sqlx.Conn, dbName, stageDBName, tableName string) error {
	ok, err := pkg.IsTableExistsIn(conn, tableName, stageDBName)
	if err != nil {
		logger.Error("error checking if table exists in database %s.%s: %s", stageDBName, tableName, err)
		return err
	}

	if !ok {
		return fmt.Errorf("table `%s` does not exist in `%s`", tableName, stageDBName)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	// 留着这里, drop table 不需要预处理触发器
	//var triggers []string
	//err = conn.SelectContext(
	//	ctx,
	//	&triggers,
	//	`SELECT TRIGGER_NAME FROM INFORMATION_SCHEMA.TRIGGERS WHERE EVENT_OBJECT_SCHEMA = ? AND EVENT_OBJECT_TABLE = ?`,
	//	dbName, tableName,
	//)
	//if err != nil {
	//	logger.Error("query trigger for %s.%s failed: %s", dbName, tableName, err)
	//	return err
	//}
	//logger.Info("query trigger for %s.%s succeeded: %v", dbName, tableName, triggers)
	//
	//for _, trigger := range triggers {
	//	_, err = conn.ExecContext(ctx, fmt.Sprintf("USE `%s`", dbName))
	//	if err != nil {
	//		logger.Error("change db to %s failed: %s", dbName, err)
	//		return err
	//	}
	//	logger.Info("change db to %s succeeded", dbName)
	//
	//	// 中控要 change db 再 drop trigger
	//	_, err = conn.ExecContext(ctx, fmt.Sprintf("DROP TRIGGER `%s`", trigger))
	//	if err != nil {
	//		logger.Error("drop trigger for %s.%s failed: %s", dbName, trigger, err)
	//		return err
	//	}
	//	logger.Info("drop trigger for %s.%s succeeded", dbName, trigger)
	//}

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf(
			"DROP TABLE IF EXISTS `%s`.`%s`",
			dbName, tableName,
		),
	)

	return err
}
