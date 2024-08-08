package pkg

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/rename_dbs/pkg"

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
		return nil, err
	}

	dbs := maps.Keys(dbTableMap)

	for k, v := range dbTableMap {
		logger.Info("%s tables: %v", k, v)
	}

	return pkg.IsDBsInUsing(conn, dbs)
}
