package pkg

import (
	"context"
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
		return err
	}

	if !ok {
		return fmt.Errorf("table `%s` does not exist in `%s`", tableName, stageDBName)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err = conn.ExecContext(
		ctx,
		fmt.Sprintf(
			"DROP TABLE IF EXISTS `%s`.`%s`",
			dbName, tableName,
		),
	)

	return err
}
