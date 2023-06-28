package spider

import (
	"sort"
	"strings"

	sq "github.com/Masterminds/squirrel"
	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"

	"dbm-services/common/go-pubpkg/cmutil"
)

// MysqlServer TODO
type MysqlServer struct {
	ServerName string `json:"Server_name" db:"Server_name"`
	Host       string `json:"Host" db:"Host"`
	Port       int    `json:"Port" db:"Port"`
	Wrapper    string `json:"Wrapper" db:"Wrapper"`
	PartValue  int    // PARTITION_DESCRIPTION
}

// TableName TODO
func (s MysqlServer) TableName() string {
	return "mysql.servers"
}

func getSpiderPartitions(servers []*MysqlServer) ([]int, error) {
	var partValues []int
	for _, r := range servers {
		if strings.HasPrefix(r.ServerName, cst.ServerNamePrefix) && r.Wrapper == cst.WrapperRemote {
			partValue := cast.ToInt(strings.TrimPrefix(r.ServerName, cst.ServerNamePrefix))
			partValues = append(partValues, partValue)
		}
	}
	// partValues 应该是连续的数字
	partValues = cmutil.UniqueInts(partValues)
	sort.Ints(partValues)
	partCount := len(partValues)
	if (partValues[partCount-1] - partValues[0] + 1) != partCount { // 判断连续
		return nil, errors.Errorf("partition error: %v", partValues)
	}
	return partValues, nil
}

// GetMysqlServers TODO
func (s MysqlServer) GetMysqlServers(db *sqlx.DB) ([]*MysqlServer, error) {
	sqlQ := sq.Select("Server_name", "Host", "Port", "Wrapper").From(s.TableName())
	var servers []*MysqlServer
	sqlStr, sqlArgs := sqlQ.MustSql()
	if err := db.Select(&servers, sqlStr, sqlArgs...); err != nil {
		// if err := sqlQ.RunWith(db).Scan(&servers); err != nil {
		return nil, err
	}
	return servers, nil
}
