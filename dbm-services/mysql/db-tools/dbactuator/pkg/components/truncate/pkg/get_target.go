package pkg

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"

	"github.com/jmoiron/sqlx"
)

func GetTarget(
	conn *sqlx.Conn,
	dbPatterns, ignoreDBs, tablePatterns, ignoreTables, systemDBs []string,
	stageDBHeader, rollbackTail string,
	shardId int, hashShard bool) (map[string][]string, error) {
	f, err := newFilter(
		dbPatterns, ignoreDBs, tablePatterns, ignoreTables, systemDBs,
		stageDBHeader, rollbackTail,
		shardId, hashShard,
	)
	if err != nil {
		logger.Error("new filter failed: %s", err.Error())
		return nil, err
	}

	res, err := f.getTarget(conn)
	if err != nil {
		logger.Error("get target failed: %s", err.Error())
		return nil, err
	}
	return res, nil
}

type filter struct {
	f *db_table_filter.DbTableFilter
}

func (c *filter) getTarget(conn *sqlx.Conn) (map[string][]string, error) {
	return c.f.GetTablesByConn(conn)
}

func newFilter(
	dbPatterns, ignoreDBs, tablePatterns, ignoreTables, systemDBs []string,
	stageDBHeader, rollbackTail string,
	shardId int, hashShard bool) (*filter, error) {

	logger.Info("original dbPatterns: %s", dbPatterns)
	logger.Info("original ignoreDBs: %s", ignoreDBs)

	ignoreDBs = append(ignoreDBs, []string{
		fmt.Sprintf("%s%%", stageDBHeader),
		fmt.Sprintf("%%%s", rollbackTail),
		fmt.Sprintf("%s%%", "bak_"),
	}...)

	if hashShard {
		dbPatterns = adjustByShardId(dbPatterns, shardId)
		ignoreDBs = adjustByShardId(ignoreDBs, shardId)
		logger.Info("adjust dbPatterns: %s", dbPatterns)
		logger.Info("adjust ignoreDBs: %s", ignoreDBs)
	}
	// 系统库要放在 shard 调整之后
	ignoreDBs = append(ignoreDBs, systemDBs...)

	_f, err := db_table_filter.NewFilter(
		dbPatterns,
		tablePatterns,
		ignoreDBs,
		ignoreTables,
	)
	if err != nil {
		return nil, err
	}

	logger.Info("db filter regex: ", _f.DbFilterRegex())
	logger.Info("table filter regex: ", _f.TableFilterRegex())

	return &filter{f: _f}, nil
}

func adjustByShardId(dbs []string, shardId int) (res []string) {
	for _, dbName := range dbs {
		if strings.HasSuffix(dbName, "%") || dbName == "*" {
			res = append(res, dbName)
		} else {
			res = append(res, fmt.Sprintf("%s_%d", dbName, shardId))
		}
	}
	return res
}
