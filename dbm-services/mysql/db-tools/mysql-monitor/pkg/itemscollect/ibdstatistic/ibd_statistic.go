// Package ibdstatistic ibd大小统计
package ibdstatistic

import (
	"database/sql"
	"log/slog"
	"regexp"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

/*
以扫描磁盘文件的方式统计 innodb 库表大小
本来计划同时实现 .frm 和 .par 文件丢失的告警
但是在 8.0 里面已经没有这两个文件了
所以就只做一个单纯统计表大小的功能
虽然都是磁盘文件扫描, 但还是没办法和 ext3_check 整合
因为不太好把文件信息缓存下来共享使用, 可能会比较大
同时经过实际测试, 50w 表的统计耗时 2s, 所以独立扫描一次问题应该也不大
*/

var name = "ibd-statistic"

var ibdExt string
var partitionPattern *regexp.Regexp
var systemDBs = []string{
	"mysql",
	"sys",
	"information_schema",
	"infodba_schema",
	"performance_schema",
	"test",
	"db_infobase",
}

func init() {
	ibdExt = ".ibd"
	partitionPattern = regexp.MustCompile(`^(.*)#[pP]#.*\.ibd`)

}

type ibdStatistic struct {
	db *sqlx.DB
}

// Run TODO
func (c *ibdStatistic) Run() (msg string, err error) {
	var dataDir sql.NullString
	err = c.db.Get(&dataDir, `SELECT @@datadir`)
	if err != nil {
		slog.Error("ibd-statistic", slog.String("error", err.Error()))
		return "", err
	}

	if !dataDir.Valid {
		err := errors.Errorf("invalid datadir: '%s'", dataDir.String)
		slog.Error("ibd-statistic", slog.String("error", err.Error()))
		return "", err
	}

	result, err := collectResult(dataDir.String)
	if err != nil {
		return "", err
	}

	err = reportMetrics(result)
	if err != nil {
		return "", err
	}

	err = reportLog(result)
	if err != nil {
		return "", err
	}

	return "", nil
}

// Name TODO
func (c *ibdStatistic) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &ibdStatistic{db: cc.MySqlDB}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}
