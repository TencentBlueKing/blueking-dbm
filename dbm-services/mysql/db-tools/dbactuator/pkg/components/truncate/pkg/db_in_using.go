package pkg

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs/pkg"
	"fmt"

	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/maps"
)

// IsDBsInUsing 要么在 spider 上执行, 要么在 backend 执行
// 所以不需要 shard 信息
func IsDBsInUsing(
	conn *sqlx.Conn,
	dbPatterns, ignoreDBs, tablePatterns, ignoreTables, systemDBs []string,
	stageDBHeader, rollbackTail string) ([]string, error) {
	dbTableMap, err := GetTarget(
		conn,
		dbPatterns, ignoreDBs, tablePatterns, ignoreTables, systemDBs,
		stageDBHeader, rollbackTail,
		0, false,
	)
	if err != nil {
		logger.Error("get target db tables error: %v", err)
		return nil, err
	}
	logger.Info("get target db tables: %v", dbTableMap)
	if dbTableMap == nil || len(dbTableMap) == 0 {
		err = fmt.Errorf("go empty db-tables")
		logger.Error("go empty db-tables: %v", err)
		return nil, err
	}

	dbs := maps.Keys(dbTableMap)

	return pkg.IsDBsInUsing(conn, dbs)
}
